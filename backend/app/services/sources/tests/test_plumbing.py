"""Tests for shared sources plumbing: ratelimit, http, outcome, text, errors.

Owner: Person 3 (backend/app/services/sources/tests/test_plumbing.py)
Reference: Contract Sections 5.5, 10, 12, Phase 1 requirements
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx
import pytest
import respx
from app.schemas import (
    AssetType,
    NormalizedCandidate,
    ProviderErrorCode,
    SourceMode,
    SourceStatus,
)
from app.services.sources.errors import ProviderError
from app.services.sources.http import request_json
from app.services.sources.outcome import build_result, should_abort_remaining_queries
from app.services.sources.ratelimit import AsyncRateLimiter
from app.services.sources.text import extract_links, sanitize_text

# =============================================================================
# 1. Fake Clock and AsyncRateLimiter Tests
# =============================================================================


class FakeClock:
    def __init__(self, start_time: float = 0.0) -> None:
        self.current_time = start_time

    def now(self) -> float:
        return self.current_time

    async def sleep(self, duration: float) -> None:
        self.current_time += duration
        # Allow other cooperative tasks to execute
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_ratelimiter_spacing_and_concurrency() -> None:
    clock = FakeClock()
    limiter = AsyncRateLimiter(min_interval_s=3.0, clock=clock.now, sleep=clock.sleep)

    start_times: list[float] = []

    async def task(task_id: int) -> None:
        async with limiter:
            start_times.append(clock.now())

    # Run 3 concurrent tasks
    await asyncio.gather(task(1), task(2), task(3))

    assert len(start_times) == 3
    assert start_times[0] == 0.0
    assert start_times[1] == 3.0
    assert start_times[2] == 6.0


@pytest.mark.asyncio
async def test_ratelimiter_cancellation_safety() -> None:
    clock = FakeClock()
    limiter = AsyncRateLimiter(min_interval_s=3.0, clock=clock.now, sleep=clock.sleep)

    # Claim first slot at t=0
    async with limiter:
        pass

    # Task 2 wants slot at t=3, but will be cancelled while waiting
    started_task3 = False

    async def waiter_to_cancel() -> None:
        async with limiter:
            pass

    async def waiter_next() -> float:
        nonlocal started_task3
        async with limiter:
            started_task3 = True
            return clock.now()

    t2 = asyncio.create_task(waiter_to_cancel())
    await asyncio.sleep(0)  # let t2 acquire the lock and enter sleep
    t2.cancel()
    with pytest.raises(asyncio.CancelledError):
        await t2

    # Task 3 should still be able to acquire slot without corrupting limiter state
    t3_start = await waiter_next()
    assert started_task3 is True
    # Next allowed slot was t=3.0 from Task 1, and Task 3 gets it
    assert t3_start == 3.0


# =============================================================================
# 2. HTTP Helper (`request_json`) Tests
# =============================================================================


@pytest.mark.asyncio
@respx.mock
async def test_request_json_200_ok() -> None:
    respx.get("https://api.example/data").mock(
        return_value=httpx.Response(200, json={"status": "ok", "count": 5})
    )

    async with httpx.AsyncClient() as client:
        data = await request_json(client, "GET", "https://api.example/data")
        assert data == {"status": "ok", "count": 5}


@pytest.mark.asyncio
@respx.mock
async def test_request_json_429_no_retry() -> None:
    route = respx.get("https://api.example/data").mock(
        return_value=httpx.Response(429, text="Too Many Requests")
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(ProviderError) as exc_info:
            await request_json(client, "GET", "https://api.example/data", retries=2)

        assert exc_info.value.error_code == ProviderErrorCode.RATE_LIMITED
        assert "429" in exc_info.value.message
        # Never retries on 429
        assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_request_json_403_and_401_no_retry() -> None:
    route_403 = respx.get("https://api.example/forbidden").mock(
        return_value=httpx.Response(403, text="Forbidden")
    )
    route_401 = respx.get("https://api.example/unauth").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(ProviderError) as exc_403:
            await request_json(client, "GET", "https://api.example/forbidden")
        assert exc_403.value.error_code == ProviderErrorCode.AUTH_REQUIRED
        assert route_403.call_count == 1

        with pytest.raises(ProviderError) as exc_401:
            await request_json(client, "GET", "https://api.example/unauth")
        assert exc_401.value.error_code == ProviderErrorCode.AUTH_REQUIRED
        assert route_401.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_request_json_500_then_200_retry() -> None:
    route = respx.get("https://api.example/flake").mock(
        side_effect=[
            httpx.Response(500, text="Internal Server Error"),
            httpx.Response(200, json={"recovered": True}),
        ]
    )

    async with httpx.AsyncClient() as client:
        data = await request_json(client, "GET", "https://api.example/flake", retries=1)
        assert data == {"recovered": True}
        assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_request_json_500_twice_fails() -> None:
    route = respx.get("https://api.example/fail500").mock(
        side_effect=[
            httpx.Response(502, text="Bad Gateway"),
            httpx.Response(503, text="Service Unavailable"),
        ]
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(ProviderError) as exc:
            await request_json(client, "GET", "https://api.example/fail500", retries=1)

        assert exc.value.error_code == ProviderErrorCode.PROVIDER_UNAVAILABLE
        assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_request_json_timeout_then_200() -> None:
    route = respx.get("https://api.example/timeout-flake").mock(
        side_effect=[
            httpx.TimeoutException("Timed out"),
            httpx.Response(200, json={"ok": True}),
        ]
    )

    async with httpx.AsyncClient() as client:
        data = await request_json(
            client, "GET", "https://api.example/timeout-flake", retries=1
        )
        assert data == {"ok": True}
        assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_request_json_timeout_twice() -> None:
    route = respx.get("https://api.example/timeout-fail").mock(
        side_effect=[
            httpx.TimeoutException("Timed out 1"),
            httpx.TimeoutException("Timed out 2"),
        ]
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(ProviderError) as exc:
            await request_json(
                client, "GET", "https://api.example/timeout-fail", retries=1
            )

        assert exc.value.error_code == ProviderErrorCode.TIMEOUT
        assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_request_json_invalid_json() -> None:
    respx.get("https://api.example/badjson").mock(
        return_value=httpx.Response(200, text="<xml>not json</xml>")
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(ProviderError) as exc:
            await request_json(client, "GET", "https://api.example/badjson")

        assert exc.value.error_code == ProviderErrorCode.INVALID_RESPONSE
        assert "not valid json" in exc.value.message.lower()


@pytest.mark.asyncio
@respx.mock
async def test_request_json_non_utf8() -> None:
    respx.get("https://api.example/badbytes").mock(
        return_value=httpx.Response(200, content=b"\xff\xfe\x00\x00invalid")
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(ProviderError) as exc:
            await request_json(client, "GET", "https://api.example/badbytes")

        assert exc.value.error_code == ProviderErrorCode.INVALID_RESPONSE
        assert "utf-8" in exc.value.message.lower()


@pytest.mark.asyncio
@respx.mock
async def test_request_json_oversized_body() -> None:
    # 5 MB + 100 bytes
    huge_data = b" " * (5 * 1024 * 1024 + 100)
    respx.get("https://api.example/huge").mock(
        return_value=httpx.Response(200, content=huge_data)
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(ProviderError) as exc:
            await request_json(client, "GET", "https://api.example/huge")

        assert exc.value.error_code == ProviderErrorCode.INVALID_RESPONSE
        assert "5 mb" in exc.value.message.lower()


@pytest.mark.asyncio
@respx.mock
async def test_request_json_network_connection_error() -> None:
    route = respx.get("https://api.example/neterr").mock(
        side_effect=[
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused retry"),
        ]
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(ProviderError) as exc:
            await request_json(client, "GET", "https://api.example/neterr", retries=1)

        assert exc.value.error_code == ProviderErrorCode.PROVIDER_UNAVAILABLE
        assert route.call_count == 2


# =============================================================================
# 3. Outcome Builder (`build_result`) Tests
# =============================================================================


def _make_candidate(cand_id: str) -> NormalizedCandidate:
    return NormalizedCandidate(
        source_id="test_source",
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier=cand_id,
        display_name=f"App {cand_id}",
        source_mode=SourceMode.LIVE,
        retrieved_at=datetime.now(UTC),
    )


def test_build_result_every_query_ok_with_candidates() -> None:
    candidates = [_make_candidate("1"), _make_candidate("2")]
    res = build_result(
        source_id="apple_itunes",
        total_queries_planned=3,
        candidates=candidates,
        queries_succeeded=3,
        failures=[],
        duration_ms=150,
        live_requests_count=3,
    )

    assert res.status == SourceStatus.CONNECTED
    assert res.source_mode == SourceMode.LIVE
    assert res.error_code is None
    assert res.message == "3 queries completed."
    assert len(res.candidates) == 2
    assert res.queries_executed == 3


def test_build_result_all_ok_zero_matches() -> None:
    res = build_result(
        source_id="apple_itunes",
        total_queries_planned=4,
        candidates=[],
        queries_succeeded=4,
        failures=[],
        duration_ms=120,
        live_requests_count=4,
    )

    assert res.status == SourceStatus.CONNECTED
    assert res.source_mode == SourceMode.LIVE
    assert res.error_code is None
    assert res.message == "4 queries completed; no matching results returned."
    assert len(res.candidates) == 0


def test_build_result_some_ok_then_429() -> None:
    candidates = [_make_candidate("1")]
    res = build_result(
        source_id="bluesky_public",
        total_queries_planned=6,
        candidates=candidates,
        queries_succeeded=4,
        failures=[(ProviderErrorCode.RATE_LIMITED, "Rate limit reached")],
        duration_ms=450,
        live_requests_count=5,
    )

    assert res.status == SourceStatus.RATE_LIMITED
    assert res.error_code == ProviderErrorCode.RATE_LIMITED
    assert res.message == "Stopped after 4 of 6 queries; partial results kept."
    assert len(res.candidates) == 1
    assert res.queries_executed == 4


def test_build_result_some_ok_some_other_fail() -> None:
    candidates = [_make_candidate("1"), _make_candidate("2")]
    res = build_result(
        source_id="apple_itunes",
        total_queries_planned=8,
        candidates=candidates,
        queries_succeeded=6,
        failures=[
            (ProviderErrorCode.TIMEOUT, "Query timed out"),
            (ProviderErrorCode.PROVIDER_UNAVAILABLE, "503 error"),
        ],
        duration_ms=800,
        live_requests_count=8,
    )

    assert res.status == SourceStatus.PARTIAL
    assert res.error_code == ProviderErrorCode.TIMEOUT
    assert (
        res.message
        == "6 of 8 queries completed; 2 failed (TIMEOUT). Partial results kept."
    )
    assert len(res.candidates) == 2


def test_build_result_all_failed_no_cache_429() -> None:
    res = build_result(
        source_id="bluesky_public",
        total_queries_planned=5,
        candidates=[],
        queries_succeeded=0,
        failures=[(ProviderErrorCode.RATE_LIMITED, "Rate limited on first query")],
        duration_ms=90,
        live_requests_count=1,
    )

    assert res.status == SourceStatus.RATE_LIMITED
    assert res.error_code == ProviderErrorCode.RATE_LIMITED
    assert res.candidates == []
    assert res.source_mode is None
    assert "0 results" not in res.message.lower()


def test_build_result_all_failed_no_cache_5xx() -> None:
    res = build_result(
        source_id="apple_itunes",
        total_queries_planned=3,
        candidates=[],
        queries_succeeded=0,
        failures=[(ProviderErrorCode.PROVIDER_UNAVAILABLE, "Apple service down")],
        duration_ms=200,
        live_requests_count=3,
    )

    assert res.status == SourceStatus.ERROR
    assert res.error_code == ProviderErrorCode.PROVIDER_UNAVAILABLE
    assert res.candidates == []
    assert res.source_mode is None
    assert res.status != SourceStatus.CONNECTED
    assert "0 results" not in res.message.lower()


def test_build_result_cached_source_mode() -> None:
    candidates = [_make_candidate("1")]
    res = build_result(
        source_id="apple_itunes",
        total_queries_planned=2,
        candidates=candidates,
        queries_succeeded=2,
        failures=[],
        duration_ms=10,
        live_requests_count=0,
        cache_hits_count=2,
    )

    assert res.source_mode == SourceMode.CACHED
    assert res.cache_hit_count == 2


def test_should_abort_remaining_queries() -> None:
    # Abort immediately on RATE_LIMITED or AUTH_REQUIRED
    assert should_abort_remaining_queries(1, ProviderErrorCode.RATE_LIMITED) is True
    assert should_abort_remaining_queries(1, ProviderErrorCode.AUTH_REQUIRED) is True

    # Do not abort on single transient error
    assert should_abort_remaining_queries(1, ProviderErrorCode.TIMEOUT) is False
    assert (
        should_abort_remaining_queries(2, ProviderErrorCode.PROVIDER_UNAVAILABLE)
        is False
    )

    # Abort after 3 consecutive transient errors
    assert should_abort_remaining_queries(3, ProviderErrorCode.TIMEOUT) is True
    assert (
        should_abort_remaining_queries(4, ProviderErrorCode.PROVIDER_UNAVAILABLE)
        is True
    )


# =============================================================================
# 4. Text Sanitizer and Link Extractor Tests
# =============================================================================


def test_sanitize_text_removes_nul_and_control_chars() -> None:
    raw = "Hello\x00World\x01\x02\x1f!\x7f"
    sanitized = sanitize_text(raw)
    assert sanitized == "HelloWorld!"


def test_sanitize_text_preserves_homoglyphs_and_unicode_untouched() -> None:
    # Cyrillic 'і' (U+0456) must NOT be folded to Latin 'i' or altered
    cyrillic_i = "\u0456"
    raw_name = f"Kaver{cyrillic_i} Bank"

    sanitized = sanitize_text(raw_name)
    assert sanitized == raw_name
    assert sanitized[5] == "\u0456"  # byte-for-byte preserved


def test_extract_links_normalizes_and_deduplicates() -> None:
    text = (
        "Visit our portal at https://KAVERI-BANK.EXAMPLE/rewards, or call us. "
        "Also check (https://kaveri-bank.example/rewards) and http://SUB.DOMAIN.EXAMPLE/path?q=1! "
        "Ignore ftp://not-http.example."
    )

    links = extract_links(text)
    # Deduplicated, lowercase host, trailing comma/parenthesis trimmed
    assert links == [
        "https://kaveri-bank.example/rewards",
        "http://sub.domain.example/path?q=1",
    ]


def test_extract_links_caps_at_10_and_300_chars() -> None:
    # 15 distinct links
    many_links = " ".join(f"https://site{i}.example/page" for i in range(15))
    links = extract_links(many_links)
    assert len(links) == 10

    # Overly long link (> 300 chars) ignored
    long_link = "https://example.com/" + ("a" * 300)
    assert extract_links(long_link) == []
