"""Hardening tests: Contract-level failure matrix across both adapters (Section A).

Owner: Person 3
Reference: Contract Sections 5.3, 5.5, 10, 11.4, 12, 15.3, Phase 9 Hardening
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
import respx

from app.schemas import (
    PlannedQuery,
    ProviderErrorCode,
    QueryPlan,
    SourceMode,
    SourceStatus,
)
from app.services.sources.apple import AppleItunesAdapter
from app.services.sources.bluesky import BlueskyPublicAdapter
from app.services.sources.cache import InMemoryCacheFake, make_cache_key
from app.services.sources.ratelimit import AsyncRateLimiter

FAILURE_MODES = [
    "429",
    "401",
    "403",
    "500",
    "502",
    "503",
    "timeout",
    "connection_reset",
    "dns_failure",
    "invalid_json",
    "wrong_shape",
    "empty_body",
    "html_body",
    "non_utf8",
    "6mb_body",
]

POSITIONS = ["first_query", "middle_query", "last_query", "every_query"]
CACHE_STATES = ["no_cache", "fresh_cache", "stale_no_fallback", "stale_with_fallback"]


def make_failure_response(mode: str) -> httpx.Response | Exception:
    """Generate mock response or network exception for failure mode."""
    if mode == "429":
        return httpx.Response(429, text="Rate limit exceeded")
    if mode == "401":
        return httpx.Response(401, text="Unauthorized")
    if mode == "403":
        return httpx.Response(403, text="Forbidden")
    if mode == "500":
        return httpx.Response(500, text="Internal Server Error")
    if mode == "502":
        return httpx.Response(502, text="Bad Gateway")
    if mode == "503":
        return httpx.Response(503, text="Service Unavailable")
    if mode == "timeout":
        return httpx.ReadTimeout("Request timed out")
    if mode == "connection_reset":
        return httpx.NetworkError("Connection reset by peer")
    if mode == "dns_failure":
        return httpx.ConnectError("getaddrinfo failed")
    if mode == "invalid_json":
        return httpx.Response(200, text="{broken json")
    if mode == "wrong_shape":
        return httpx.Response(200, json={"some_other_key": "not_an_array"})
    if mode == "empty_body":
        return httpx.Response(200, text="")
    if mode == "html_body":
        return httpx.Response(200, text="<html><body>Error</body></html>")
    if mode == "non_utf8":
        return httpx.Response(200, content=b"\x80\x81\xff\xfe")
    if mode == "6mb_body":
        return httpx.Response(200, content=b"A" * (6 * 1024 * 1024))
    raise ValueError(f"Unknown failure mode {mode}")


def expected_error_code(mode: str) -> ProviderErrorCode:
    if mode == "429":
        return ProviderErrorCode.RATE_LIMITED
    if mode in ("401", "403"):
        return ProviderErrorCode.AUTH_REQUIRED
    if mode in ("500", "502", "503", "connection_reset", "dns_failure"):
        return ProviderErrorCode.PROVIDER_UNAVAILABLE
    if mode == "timeout":
        return ProviderErrorCode.TIMEOUT
    return ProviderErrorCode.INVALID_RESPONSE


class TestFailureMatrix:
    """Contract-level failure matrix across adapters, failure modes, positions, and cache states."""

    @pytest.mark.parametrize("adapter_name", ["apple", "bluesky"])
    @pytest.mark.asyncio
    async def test_provider_failure_is_not_clean_result(
        self, adapter_name: str
    ) -> None:
        """Failure with no cache -> candidates == [] AND status != CONNECTED AND error_code is set AND message is non-empty."""
        for mode in FAILURE_MODES:
            with respx.mock:
                resp_or_exc = make_failure_response(mode)
                if adapter_name == "apple":
                    respx.get("https://itunes.apple.com/search").mock(
                        side_effect=resp_or_exc
                    )
                    adapter = AppleItunesAdapter(rate_limiter=AsyncRateLimiter(0.0))
                else:
                    respx.get(
                        "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
                    ).mock(side_effect=resp_or_exc)
                    adapter = BlueskyPublicAdapter(rate_limiter=AsyncRateLimiter(0.0))

                plan = QueryPlan(
                    brand_id=uuid4(),
                    queries=[PlannedQuery(term="kaveri", kind="EXACT", priority=1)],
                )

                res = await adapter.search(plan)

                assert res.candidates == [], (
                    f"Expected candidates == [] for {adapter_name} mode {mode}"
                )
                assert res.status != SourceStatus.CONNECTED, (
                    f"Status must NOT be CONNECTED for {adapter_name} mode {mode}"
                )
                assert res.error_code is not None, (
                    f"error_code must be set for {adapter_name} mode {mode}"
                )
                assert res.message != "", (
                    f"message must be non-empty for {adapter_name} mode {mode}"
                )
                assert "0 results" not in res.message.lower()
                assert "safe" not in res.message.lower()
                assert "all clear" not in res.message.lower()

    @pytest.mark.parametrize("adapter_name", ["bluesky", "apple"])
    @pytest.mark.asyncio
    @respx.mock
    async def test_contract_example_stopped_after_4_of_6_queries(
        self, adapter_name: str
    ) -> None:
        """Section 11.4 example: Stopped after 4 of 6 queries; partial results kept."""
        plan = QueryPlan(
            brand_id=uuid4(),
            queries=[
                PlannedQuery(term=f"term_{i}", kind="EXACT", priority=i + 1)
                for i in range(6)
            ],
        )

        if adapter_name == "bluesky":
            # First 4 queries return 3 candidates each (total 12). 5th query returns 429.
            actors_batches = [
                [
                    {"did": f"did:plc:a_{q}_{i}", "handle": f"user_{q}_{i}.bsky.social"}
                    for i in range(3)
                ]
                for q in range(4)
            ]
            route_search = respx.get(
                "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
            )
            route_search.side_effect = [
                httpx.Response(200, json={"actors": actors_batches[0]}),
                httpx.Response(200, json={"actors": actors_batches[1]}),
                httpx.Response(200, json={"actors": actors_batches[2]}),
                httpx.Response(200, json={"actors": actors_batches[3]}),
                httpx.Response(429, text="Rate limit exceeded"),
            ]
            respx.get(
                "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles"
            ).respond(200, json={"profiles": []})

            adapter = BlueskyPublicAdapter(rate_limiter=AsyncRateLimiter(0.0))
            res = await adapter.search(plan)

            assert res.source_id == "bluesky_public"
            assert res.status == SourceStatus.RATE_LIMITED
            assert res.source_mode == SourceMode.LIVE
            assert res.queries_executed == 4
            assert len(res.candidates) == 12
            assert res.cache_hit_count == 0
            assert res.error_code == ProviderErrorCode.RATE_LIMITED
            assert res.message == "Stopped after 4 of 6 queries; partial results kept."

        else:
            # Apple adapter: 4 queries return apps, 5th hits 429
            route_search = respx.get("https://itunes.apple.com/search")
            route_search.side_effect = [
                httpx.Response(
                    200,
                    json={
                        "resultCount": 1,
                        "results": [
                            {
                                "trackId": 100 + q,
                                "trackName": f"App {q}",
                                "kind": "software",
                            }
                        ],
                    },
                )
                for q in range(4)
            ] + [httpx.Response(429, text="Rate limited")]

            adapter = AppleItunesAdapter(rate_limiter=AsyncRateLimiter(0.0))
            res = await adapter.search(plan)

            assert res.source_id == "apple_itunes"
            assert res.status == SourceStatus.RATE_LIMITED
            assert res.source_mode == SourceMode.LIVE
            assert res.queries_executed == 4
            assert len(res.candidates) == 4
            assert res.cache_hit_count == 0
            assert res.error_code == ProviderErrorCode.RATE_LIMITED
            assert res.message == "Stopped after 4 of 6 queries; partial results kept."

    @pytest.mark.parametrize("adapter_name", ["apple", "bluesky"])
    @pytest.mark.parametrize("mode", FAILURE_MODES)
    @pytest.mark.parametrize("position", POSITIONS)
    @pytest.mark.parametrize("cache_state", CACHE_STATES)
    @pytest.mark.asyncio
    async def test_full_failure_matrix_cell(
        self,
        adapter_name: str,
        mode: str,
        position: str,
        cache_state: str,
    ) -> None:
        """One test per cell: 15 failure modes x 4 positions x 4 cache states across both adapters."""
        with respx.mock:
            terms = ["term_alpha", "term_beta", "term_gamma"]
            plan = QueryPlan(
                brand_id=uuid4(),
                queries=[
                    PlannedQuery(term=t, kind="EXACT", priority=i + 1)
                    for i, t in enumerate(terms)
                ],
            )

            # Setup cache
            cache = InMemoryCacheFake(default_ttl_s=3600)
            stale_time = datetime.now(UTC) - timedelta(hours=5)
            fresh_time = datetime.now(UTC) - timedelta(minutes=5)

            apple_good = {
                "resultCount": 1,
                "results": [
                    {"trackId": 555, "trackName": "Cached App", "kind": "software"}
                ],
            }
            bluesky_good = {
                "actors": [{"did": "did:plc:cached1", "handle": "cached.bsky.social"}]
            }

            if cache_state in (
                "fresh_cache",
                "stale_no_fallback",
                "stale_with_fallback",
            ):
                is_fresh = cache_state == "fresh_cache"
                cached_time = fresh_time if is_fresh else stale_time
                for t in terms:
                    if adapter_name == "apple":
                        key = make_cache_key(
                            "apple_itunes",
                            "search",
                            {
                                "country": "in",
                                "entity": "software",
                                "limit": 50,
                                "term": t,
                            },
                        )
                        cache.put(
                            key,
                            "apple_itunes",
                            {},
                            apple_good,
                            retrieved_at=cached_time,
                        )
                    else:
                        key = make_cache_key(
                            "bluesky_public", "searchActors", {"limit": 50, "q": t}
                        )
                        cache.put(
                            key,
                            "bluesky_public",
                            {},
                            bluesky_good,
                            retrieved_at=cached_time,
                        )
                        # Pre-cache enrichment for the discovered actor
                        key_enrich = make_cache_key(
                            "bluesky_public",
                            "getProfiles",
                            {"actors": ["did:plc:cached1"]},
                        )
                        cache.put(
                            key_enrich,
                            "bluesky_public",
                            {},
                            {
                                "profiles": [
                                    {
                                        "did": "did:plc:cached1",
                                        "handle": "cached.bsky.social",
                                    }
                                ]
                            },
                            retrieved_at=cached_time,
                        )

            failing_terms: set[str] = set()
            for idx, t in enumerate(terms):
                if (
                    position == "every_query"
                    or position == "first_query"
                    and idx == 0
                    or position == "middle_query"
                    and idx == 1
                    or position == "last_query"
                    and idx == 2
                ):
                    failing_terms.add(t)

            def make_term_handler(adapter: str, f_mode: str, f_terms: set[str]):
                def handler(request: httpx.Request) -> httpx.Response:
                    param_key = "term" if adapter == "apple" else "q"
                    term_val = request.url.params.get(param_key, "")
                    if term_val in f_terms:
                        outcome = make_failure_response(f_mode)
                        if isinstance(outcome, Exception):
                            raise outcome
                        return outcome
                    if adapter == "apple":
                        return httpx.Response(
                            200,
                            json={
                                "resultCount": 1,
                                "results": [
                                    {
                                        "trackId": 999,
                                        "trackName": f"Live {term_val}",
                                        "kind": "software",
                                    }
                                ],
                            },
                        )
                    return httpx.Response(
                        200,
                        json={
                            "actors": [
                                {
                                    "did": f"did:plc:{term_val}",
                                    "handle": f"{term_val}.bsky.social",
                                }
                            ]
                        },
                    )

                return handler

            if adapter_name == "apple":
                respx.get("https://itunes.apple.com/search").mock(
                    side_effect=make_term_handler("apple", mode, failing_terms)
                )
                adapter = AppleItunesAdapter(
                    cache=cache, rate_limiter=AsyncRateLimiter(0.0)
                )
            else:
                respx.get(
                    "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
                ).mock(side_effect=make_term_handler("bluesky", mode, failing_terms))
                respx.get(
                    "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles"
                ).respond(200, json={"profiles": []})
                adapter = BlueskyPublicAdapter(
                    cache=cache, rate_limiter=AsyncRateLimiter(0.0)
                )

            allow_stale = cache_state == "stale_with_fallback"
            res = await adapter.search(plan, allow_stale_cache=allow_stale)

            # Assertions for each cell
            if cache_state == "fresh_cache":
                # Network not called; served from fresh cache
                assert res.status == SourceStatus.CONNECTED
                assert res.source_mode == SourceMode.CACHED
                expected_hits = 3 if adapter_name == "apple" else 4
                assert res.cache_hit_count == expected_hits
                assert res.error_code is None
                assert res.queries_executed == 3
                assert len(res.candidates) > 0

            elif cache_state == "stale_with_fallback":
                # Stale cache rescues failing queries
                assert res.source_mode == SourceMode.CACHED
                assert res.cache_hit_count > 0
                assert res.queries_executed > 0
                assert len(res.candidates) > 0
                if position in (
                    "first_query",
                    "middle_query",
                    "last_query",
                    "every_query",
                ):
                    assert res.status == SourceStatus.PARTIAL
                    assert res.error_code == expected_error_code(mode)
                    assert "Showing cached results from" in res.message

            else:
                # no_cache or stale_no_fallback
                if position == "every_query":
                    assert res.candidates == []
                    assert res.queries_executed == 0
                    assert res.source_mode is None
                    assert res.error_code == expected_error_code(mode)
                    if mode == "429":
                        assert res.status == SourceStatus.RATE_LIMITED
                    else:
                        assert res.status == SourceStatus.ERROR
                    assert res.message != ""
                    assert "0 results" not in res.message.lower()

                elif position == "first_query":
                    if mode in ("429", "401", "403"):
                        # Stopped immediately
                        assert res.candidates == []
                        assert res.queries_executed == 0
                        assert res.error_code == expected_error_code(mode)
                    else:
                        # Transient error: remaining queries succeeded
                        assert res.queries_executed == 2
                        assert len(res.candidates) > 0
                        assert res.status == SourceStatus.PARTIAL
                        assert res.error_code == expected_error_code(mode)

                elif position == "middle_query":
                    if mode == "429":
                        assert res.status == SourceStatus.RATE_LIMITED
                        assert res.queries_executed == 1
                        assert res.error_code == ProviderErrorCode.RATE_LIMITED
                        assert "Stopped after 1 of 3 queries" in res.message
                    elif mode in ("401", "403"):
                        assert res.status == SourceStatus.PARTIAL
                        assert res.queries_executed == 1
                        assert res.error_code == expected_error_code(mode)
                    else:
                        assert res.status == SourceStatus.PARTIAL
                        assert res.queries_executed == 2
                        assert res.error_code == expected_error_code(mode)

                elif position == "last_query":
                    if mode == "429":
                        assert res.status == SourceStatus.RATE_LIMITED
                        assert res.queries_executed == 2
                        assert res.error_code == ProviderErrorCode.RATE_LIMITED
                        assert "Stopped after 2 of 3 queries" in res.message
                    else:
                        assert res.status == SourceStatus.PARTIAL
                        assert res.queries_executed == 2
                        assert res.error_code == expected_error_code(mode)
