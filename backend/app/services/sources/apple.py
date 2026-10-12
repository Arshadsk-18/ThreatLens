"""Apple App Store (iTunes Search & Lookup) source adapter.

Owner: Person 3 (backend/app/services/sources/apple.py)
Reference: Contract Sections 5.5, 5.6, 11.3, 12, 13.1
"""

from __future__ import annotations

import contextlib
import os
import re
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from app.schemas import (
    AssetType,
    NormalizedCandidate,
    ProviderErrorCode,
    QueryPlan,
    SourceHealth,
    SourceMode,
    SourceResult,
    SourceStatus,
)

from .cache import CacheRepo, InMemoryCacheFake, make_cache_key
from .errors import ProviderError
from .http import request_json
from .outcome import build_result, should_abort_remaining_queries
from .ratelimit import APPLE_LIMITER, AsyncRateLimiter
from .text import extract_links, sanitize_text

# Regex patterns for input validation
APPLE_URL_PATTERN = re.compile(
    r"^https://apps\.apple\.com/(?:[a-zA-Z]{2}/)?app/(?:[^/]+/)?id(\d+)",
    re.IGNORECASE,
)
BUNDLE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._\-]+$")


def parse_apple_date(val: Any) -> datetime | None:
    """Parse iTunes releaseDate into timezone-aware UTC datetime."""
    if not val or not isinstance(val, str):
        return None
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except (ValueError, TypeError):
        return None


def map_apple_item(
    item: dict[str, Any],
    source_mode: SourceMode = SourceMode.LIVE,
    retrieved_at: datetime | None = None,
    matched_query: str | None = None,
) -> NormalizedCandidate:
    """Map a raw Apple iTunes item dict to NormalizedCandidate per Section 13.1."""
    now_utc = retrieved_at or datetime.now(UTC)
    track_id = str(item.get("trackId", "")).strip()

    bundle_id = str(item["bundleId"]).strip() if item.get("bundleId") else None
    secondary_identifiers: dict[str, str] = {}
    if bundle_id:
        secondary_identifiers["bundle_id"] = bundle_id

    artist_id = (
        str(item["artistId"]).strip() if item.get("artistId") is not None else None
    )

    # External links via extract-style validation
    seller_url = item.get("sellerUrl")
    external_links: list[str] = []
    if seller_url and isinstance(seller_url, str):
        external_links = extract_links(seller_url)

    # Largest available artwork per spike (artworkUrl512, fallback to 100, then 60)
    icon_url = (
        item.get("artworkUrl512")
        or item.get("artworkUrl100")
        or item.get("artworkUrl60")
    )

    # Name sanitization: strip NUL/control characters without altering Cyrillic/homoglyphs
    display_name = sanitize_text(str(item.get("trackName", ""))) or ""
    publisher_name = (
        sanitize_text(str(item["sellerName"])) if item.get("sellerName") else None
    )
    description = (
        sanitize_text(str(item["description"])) if item.get("description") else None
    )
    category = (
        sanitize_text(str(item["primaryGenreName"]))
        if item.get("primaryGenreName")
        else None
    )

    rating_count: int | None = None
    rating_val = item.get("userRatingCount")
    if isinstance(rating_val, (int, float)):
        rating_count = int(rating_val)
    elif isinstance(rating_val, str) and rating_val.strip().isdigit():
        rating_count = int(rating_val.strip())

    canonical_url = (
        str(item["trackViewUrl"]).strip() if item.get("trackViewUrl") else None
    )

    return NormalizedCandidate(
        source_id="apple_itunes",
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier=track_id,
        secondary_identifiers=secondary_identifiers,
        display_name=display_name,
        handle=None,
        publisher_name=publisher_name,
        developer_id=artist_id,
        description=description,
        category=category,
        external_links=external_links,
        icon_url=str(icon_url).strip() if icon_url else None,
        icon_hash=None,
        canonical_url=canonical_url,
        created_at_source=parse_apple_date(item.get("releaseDate")),
        followers=None,
        following=None,
        posts_count=None,
        rating_count=rating_count,
        source_mode=source_mode,
        retrieved_at=now_utc,
        matched_queries=[matched_query] if matched_query else [],
    )


class AppleItunesAdapter:
    """SourceAdapter for the Apple App Store via iTunes Search and Lookup APIs.

    Follows Contract Section 12 & 13.1.
    """

    source_id: str = "apple_itunes"

    def __init__(
        self,
        country: str | None = None,
        timeout_s: float = 8.0,
        rate_limiter: AsyncRateLimiter | None = None,
        min_interval_s: float = 3.0,
        client: httpx.AsyncClient | None = None,
        cache: CacheRepo | None = None,
        ttl_s: int | None = None,
    ) -> None:
        self.country = country or os.environ.get("APPLE_COUNTRY", "in")
        self.timeout_s = timeout_s
        if rate_limiter is not None:
            self.rate_limiter = rate_limiter
        elif min_interval_s == 3.0:
            self.rate_limiter = APPLE_LIMITER
        else:
            self.rate_limiter = AsyncRateLimiter(min_interval_s=min_interval_s)

        self._external_client = client
        self.cache: CacheRepo = cache or InMemoryCacheFake()
        try:
            default_ttl = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))
        except ValueError:
            default_ttl = 3600
        self.ttl_s = ttl_s if ttl_s is not None else default_ttl

        # Session health tracker: reports contract default until real requests complete
        self._last_health_status: SourceStatus = SourceStatus.CONNECTED
        self._last_health_message: str = "No request made yet."
        self._last_checked_at: datetime | None = None

    @contextlib.asynccontextmanager
    async def _get_client(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._external_client is not None:
            yield self._external_client
        else:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_s)
            ) as client:
                yield client

    def _record_health(self, status: SourceStatus, message: str) -> None:
        self._last_health_status = status
        self._last_health_message = message
        self._last_checked_at = datetime.now(UTC)

    async def health_check(self, *, force_refresh: bool = False) -> SourceHealth:
        """Report source health.

        Before any request has been made this session, reports CONNECTED with
        message 'No request made yet.' and last_checked_at=None.
        After requests, reports the last real outcome.
        If force_refresh is True, performs a minimal live request through the limiter.
        """
        if force_refresh:
            try:
                async with self._get_client() as client:
                    await request_json(
                        client,
                        "GET",
                        "https://itunes.apple.com/search",
                        params={
                            "term": "apple",
                            "entity": "software",
                            "country": self.country,
                            "limit": 1,
                        },
                        timeout=self.timeout_s,
                        limiter=self.rate_limiter,
                    )
                self._record_health(
                    SourceStatus.CONNECTED, "Live catalog search available."
                )
            except ProviderError as err:
                if err.error_code == ProviderErrorCode.RATE_LIMITED:
                    self._record_health(
                        SourceStatus.RATE_LIMITED, "Provider rate limit active."
                    )
                elif err.error_code == ProviderErrorCode.AUTH_REQUIRED:
                    self._record_health(
                        SourceStatus.ERROR, "Provider authentication failed."
                    )
                else:
                    self._record_health(
                        SourceStatus.ERROR, "Provider unavailable or timed out."
                    )

        return SourceHealth(
            source_id=self.source_id,
            display_name="Apple App Store search",
            platform="apple_app_store",
            asset_types=[AssetType.IOS_APP],
            status=self._last_health_status,
            supported_modes=[SourceMode.LIVE, SourceMode.CACHED],
            default_mode=SourceMode.LIVE,
            last_checked_at=self._last_checked_at,
            rate_limit_note="About 20 requests per minute",
            message=self._last_health_message,
        )

    async def _fetch_query(
        self,
        client: httpx.AsyncClient,
        term: str,
        limit: int,
        *,
        force_refresh: bool = False,
        allow_stale_cache: bool = False,
    ) -> tuple[dict[str, Any], SourceMode, datetime, bool, ProviderErrorCode | None]:
        """Single seam to obtain raw query JSON payload (cached or live)."""
        params = {
            "country": self.country,
            "entity": "software",
            "limit": limit,
            "term": term.lower(),
        }
        cache_key = make_cache_key(self.source_id, "search", params)

        if not force_refresh:
            cached = self.cache.get(cache_key, max_age_s=self.ttl_s)
            if cached is not None and isinstance(cached.response, dict):
                return (
                    cached.response,
                    SourceMode.CACHED,
                    cached.retrieved_at,
                    False,
                    None,
                )

        search_url = "https://itunes.apple.com/search"
        request_params = {
            "term": term,
            "entity": "software",
            "country": self.country,
            "limit": limit,
        }

        try:
            now_utc = datetime.now(UTC)
            data = await request_json(
                client,
                "GET",
                search_url,
                params=request_params,
                timeout=self.timeout_s,
                limiter=self.rate_limiter,
            )

            if (
                not isinstance(data, dict)
                or "results" not in data
                or not isinstance(data["results"], list)
            ):
                raise ProviderError(
                    ProviderErrorCode.INVALID_RESPONSE,
                    "Malformed response from Apple: results array missing.",
                )

            self.cache.put(cache_key, self.source_id, request_params, data)
            cached_rec = self.cache.get(cache_key, max_age_s=None)
            stored_time = cached_rec.retrieved_at if cached_rec else now_utc
            return data, SourceMode.LIVE, stored_time, False, None

        except ProviderError as err:
            if allow_stale_cache:
                stale = self.cache.get(cache_key, max_age_s=None)
                if stale is not None and isinstance(stale.response, dict):
                    return (
                        stale.response,
                        SourceMode.CACHED,
                        stale.retrieved_at,
                        True,
                        err.error_code,
                    )
            raise

    async def search(
        self,
        plan: QueryPlan,
        limit: int = 50,
        *,
        force_refresh: bool = False,
        allow_stale_cache: bool = False,
    ) -> SourceResult:
        """Execute brand queries against Apple iTunes Search."""
        t0 = time.monotonic()
        now_utc = datetime.now(UTC)
        per_query_limit = min(max(1, limit), 50)

        # Query hygiene: strip, collapse whitespace, clip to 100 chars, skip empty
        planned_terms: list[str] = []
        for pq in plan.queries:
            cleaned = re.sub(r"\s+", " ", pq.term).strip()[:100]
            if cleaned and cleaned not in planned_terms:
                planned_terms.append(cleaned)

        if not planned_terms:
            return build_result(
                source_id=self.source_id,
                total_queries_planned=0,
                candidates=[],
                queries_succeeded=0,
                failures=[],
                duration_ms=0,
                retrieved_at=now_utc,
            )

        candidate_map: dict[str, NormalizedCandidate] = {}
        failures: list[tuple[ProviderErrorCode, str]] = []
        queries_succeeded = 0
        live_requests_count = 0
        cache_hits_count = 0
        consecutive_failures = 0
        stale_records_used = False
        stale_cache_time: datetime | None = None
        stale_error_code: ProviderErrorCode | None = None

        async with self._get_client() as client:
            for term in planned_terms:
                try:
                    (
                        data,
                        mode,
                        fetched_at,
                        is_stale,
                        err_code,
                    ) = await self._fetch_query(
                        client,
                        term,
                        per_query_limit,
                        force_refresh=force_refresh,
                        allow_stale_cache=allow_stale_cache,
                    )
                    queries_succeeded += 1
                    consecutive_failures = 0
                    if mode == SourceMode.LIVE:
                        live_requests_count += 1
                        self._record_health(
                            SourceStatus.CONNECTED, "Live catalog search available."
                        )
                    else:
                        cache_hits_count += 1
                        if is_stale:
                            stale_records_used = True
                            stale_cache_time = fetched_at
                            stale_error_code = err_code

                    for item in data.get("results", []):
                        if not isinstance(item, dict):
                            continue
                        # Skip individual malformed items (no trackId or no trackName)
                        if not item.get("trackId") or not item.get("trackName"):
                            continue

                        # Skip items that are not software
                        kind = item.get("kind")
                        wrapper = item.get("wrapperType")
                        if (
                            kind
                            and kind != "software"
                            and wrapper
                            and wrapper != "software"
                        ):
                            continue

                        # Re-normalize from raw payload on every read (lane decision)
                        c = map_apple_item(
                            item,
                            source_mode=mode,
                            retrieved_at=fetched_at,
                            matched_query=term,
                        )
                        track_id = c.stable_identifier
                        if track_id in candidate_map:
                            if term not in candidate_map[track_id].matched_queries:
                                candidate_map[track_id].matched_queries.append(term)
                        else:
                            candidate_map[track_id] = c

                except ProviderError as err:
                    consecutive_failures += 1
                    failures.append((err.error_code, err.message))

                    if err.error_code == ProviderErrorCode.RATE_LIMITED:
                        self._record_health(
                            SourceStatus.RATE_LIMITED, "Provider rate limit active."
                        )
                    elif err.error_code == ProviderErrorCode.AUTH_REQUIRED:
                        self._record_health(
                            SourceStatus.ERROR, "Provider authentication failed."
                        )
                    else:
                        self._record_health(
                            SourceStatus.ERROR, "Provider unavailable or timed out."
                        )

                    if should_abort_remaining_queries(
                        consecutive_failures, err.error_code
                    ):
                        break

        # Total candidates hard-capped at 50 keeping higher-priority query results first
        candidates = list(candidate_map.values())[:50]
        duration_ms = int((time.monotonic() - t0) * 1000)

        # Stale cache fallback outcome rule
        if stale_records_used and queries_succeeded > 0:
            time_str = (
                stale_cache_time.strftime("%H:%M UTC")
                if stale_cache_time
                else "earlier"
            )
            code_label = stale_error_code.value if stale_error_code else "ERROR"
            msg = f"Provider unavailable ({code_label}). Showing cached results from {time_str}."
            return SourceResult(
                source_id=self.source_id,
                status=SourceStatus.PARTIAL,
                source_mode=SourceMode.CACHED,
                retrieved_at=stale_cache_time or now_utc,
                candidates=candidates,
                queries_executed=queries_succeeded,
                cache_hit_count=cache_hits_count,
                error_code=stale_error_code,
                message=msg,
                duration_ms=duration_ms,
            )

        return build_result(
            source_id=self.source_id,
            total_queries_planned=len(planned_terms),
            candidates=candidates,
            queries_succeeded=queries_succeeded,
            failures=failures,
            duration_ms=duration_ms,
            live_requests_count=live_requests_count,
            cache_hits_count=cache_hits_count,
            retrieved_at=now_utc,
        )

    async def lookup(self, identifier: str) -> NormalizedCandidate | None:
        """Lookup by allowlisted store URL, track ID, or bundle ID (prefill).

        Returns None if not found or invalid input.
        Raises ProviderError if provider fails.
        """
        raw = identifier.strip()
        track_id: str | None = None
        bundle_id: str | None = None

        if len(raw) > 155 and not raw.startswith("https://"):
            return None

        # Check for URL
        if raw.startswith(("http://", "https://")):
            parsed = urlparse(raw)
            if parsed.scheme.lower() != "https":
                return None
            if parsed.netloc.lower() not in ("apps.apple.com", "itunes.apple.com"):
                return None
            m = APPLE_URL_PATTERN.match(raw)
            if not m:
                return None
            track_id = m.group(1)
        elif raw.isdigit() and len(raw) <= 155:
            track_id = raw
        elif BUNDLE_ID_PATTERN.match(raw) and len(raw) <= 155:
            bundle_id = raw
        else:
            return None

        lookup_url = "https://itunes.apple.com/lookup"
        params: dict[str, Any] = {"country": self.country}
        if track_id:
            params["id"] = track_id
        else:
            params["bundleId"] = bundle_id

        async with self._get_client() as client:
            data = await request_json(
                client,
                "GET",
                lookup_url,
                params=params,
                timeout=self.timeout_s,
                limiter=self.rate_limiter,
            )

        if not isinstance(data, dict):
            raise ProviderError(
                ProviderErrorCode.INVALID_RESPONSE,
                "Malformed response from Apple lookup: root must be an object.",
            )

        results = data.get("results")
        if not results or not isinstance(results, list) or len(results) == 0:
            return None

        item = results[0]
        if (
            not isinstance(item, dict)
            or not item.get("trackId")
            or not item.get("trackName")
        ):
            return None

        self._record_health(SourceStatus.CONNECTED, "Live catalog search available.")
        return map_apple_item(
            item, source_mode=SourceMode.LIVE, retrieved_at=datetime.now(UTC)
        )


# Backward compatibility alias
AppleSourceAdapter = AppleItunesAdapter

__all__ = [
    "AppleItunesAdapter",
    "AppleSourceAdapter",
    "map_apple_item",
    "parse_apple_date",
]
