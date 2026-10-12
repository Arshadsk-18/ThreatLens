"""Pure function and helper to construct SourceResult from query outcomes.

Owner: Person 3 (backend/app/services/sources/outcome.py)
Reference: Contract Sections 5.3, 5.5, 10, 11.4, 12
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from app.schemas import (
    NormalizedCandidate,
    ProviderErrorCode,
    SourceMode,
    SourceResult,
    SourceStatus,
)


def should_abort_remaining_queries(
    consecutive_failures: int,
    error_code: ProviderErrorCode,
) -> bool:
    """Stop-early rule (Lane decision).

    Rules:
    - Stop immediately on RATE_LIMITED (429) to respect provider backoff.
    - Stop immediately on AUTH_REQUIRED (401/403) since credentials/auth will not change.
    - For transient errors (TIMEOUT, PROVIDER_UNAVAILABLE, INVALID_RESPONSE), continue
      evaluating queries but abort if 3 consecutive queries fail.
    """
    if error_code in (ProviderErrorCode.RATE_LIMITED, ProviderErrorCode.AUTH_REQUIRED):
        return True
    return consecutive_failures >= 3


def build_result(
    source_id: str,
    total_queries_planned: int,
    candidates: Sequence[NormalizedCandidate],
    queries_succeeded: int,
    failures: Sequence[tuple[ProviderErrorCode, str]],
    duration_ms: int,
    *,
    live_requests_count: int = 0,
    cache_hits_count: int = 0,
    retrieved_at: datetime | None = None,
) -> SourceResult:
    """Build a SourceResult from per-query execution outcomes according to strict contract rules.

    Contract Rules:
    1. Every query ok -> CONNECTED, message "<n> queries completed."
    2. All ok but zero matches -> CONNECTED, candidates == [],
       message "<n> queries completed; no matching results returned."
    3. Some ok, then 429 -> RATE_LIMITED, error_code RATE_LIMITED, partial candidates kept,
       message "Stopped after <k> of <n> queries; partial results kept."
    4. Some ok, some other fail -> PARTIAL, error_code = first failure, partial candidates kept,
       message "<k> of <n> queries completed; <m> failed (<CODE>). Partial results kept."
    5. ALL failed, no cache -> status RATE_LIMITED if 429 else ERROR, error_code set,
       candidates == [], message states the failure in plain words. NEVER CONNECTED. NEVER "0 results".
    6. source_mode: LIVE if any request hit the provider, CACHED if every query was served from cache,
       None only when failed with no usable candidates or not connected.
    7. queries_executed = queries that produced usable data (live or cache).
    """
    now_utc = retrieved_at or datetime.now(UTC)
    candidates_list = list(candidates)

    # Determine source_mode
    if queries_succeeded == 0 and not candidates_list:
        resolved_source_mode: SourceMode | None = None
        final_retrieved_at: datetime | None = None
    elif live_requests_count > 0:
        resolved_source_mode = SourceMode.LIVE
        final_retrieved_at = now_utc
    elif cache_hits_count > 0:
        resolved_source_mode = SourceMode.CACHED
        final_retrieved_at = now_utc
    else:
        resolved_source_mode = SourceMode.LIVE
        final_retrieved_at = now_utc

    # Case A: No failures occurred
    if not failures:
        if not candidates_list:
            msg = f"{total_queries_planned} queries completed; no matching results returned."
        else:
            msg = f"{total_queries_planned} queries completed."

        return SourceResult(
            source_id=source_id,
            status=SourceStatus.CONNECTED,
            source_mode=resolved_source_mode,
            retrieved_at=final_retrieved_at,
            candidates=candidates_list,
            queries_executed=queries_succeeded,
            cache_hit_count=cache_hits_count,
            error_code=None,
            message=msg,
            duration_ms=duration_ms,
        )

    # Identify if a 429 rate limit occurred
    rate_limited_failure = any(
        code == ProviderErrorCode.RATE_LIMITED for code, _ in failures
    )

    # Case B: ALL planned queries failed (and no usable candidates obtained)
    if queries_succeeded == 0 and not candidates_list:
        first_err_code, first_err_msg = failures[0]
        if rate_limited_failure:
            status = SourceStatus.RATE_LIMITED
            err_code = ProviderErrorCode.RATE_LIMITED
            msg = (
                first_err_msg
                or f"Provider rate limit exceeded on all {total_queries_planned} queries."
            )
        else:
            status = SourceStatus.ERROR
            err_code = first_err_code
            msg = (
                first_err_msg
                or f"Provider error on all {total_queries_planned} queries ({first_err_code.value})."
            )

        return SourceResult(
            source_id=source_id,
            status=status,
            source_mode=None,
            retrieved_at=None,
            candidates=[],
            queries_executed=0,
            cache_hit_count=cache_hits_count,
            error_code=err_code,
            message=msg,
            duration_ms=duration_ms,
        )

    # Case C: Some queries succeeded, but at least one failed (partial result kept)
    if rate_limited_failure:
        return SourceResult(
            source_id=source_id,
            status=SourceStatus.RATE_LIMITED,
            source_mode=resolved_source_mode,
            retrieved_at=final_retrieved_at,
            candidates=candidates_list,
            queries_executed=queries_succeeded,
            cache_hit_count=cache_hits_count,
            error_code=ProviderErrorCode.RATE_LIMITED,
            message=f"Stopped after {queries_succeeded} of {total_queries_planned} queries; partial results kept.",
            duration_ms=duration_ms,
        )

    first_err_code, _ = failures[0]
    failed_count = len(failures)
    return SourceResult(
        source_id=source_id,
        status=SourceStatus.PARTIAL,
        source_mode=resolved_source_mode,
        retrieved_at=final_retrieved_at,
        candidates=candidates_list,
        queries_executed=queries_succeeded,
        cache_hit_count=cache_hits_count,
        error_code=first_err_code,
        message=(
            f"{queries_succeeded} of {total_queries_planned} queries completed; "
            f"{failed_count} failed ({first_err_code.value}). Partial results kept."
        ),
        duration_ms=duration_ms,
    )
