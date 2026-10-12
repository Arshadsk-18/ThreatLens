"""Unit and respx tests for Phase 4 Cache plumbing and adapter integration.

Owner: Person 3 (backend/app/services/sources/tests/test_cache.py)
Reference: Contract Sections 5.5, 12, Phase 4 specs
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
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
from app.services.sources.cache import (
    CachedResponse,
    InMemoryCacheFake,
    make_cache_key,
)

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "tests" / "fixtures"
APPLE_SAMPLE_PATH = FIXTURES_DIR / "apple_search_bank_sample.json"
BSKY_SEARCH_PATH = FIXTURES_DIR / "bsky_search_actors_bank.json"
BSKY_PROFILES_PATH = FIXTURES_DIR / "bsky_get_profiles.json"


def test_cache_key_stability_and_sensitivity() -> None:
    # 1. Stability: same parameters in different dict key order yield the identical hash
    p1 = {"term": "kaveri bank", "country": "in", "limit": 25}
    p2 = {"limit": 25, "term": "kaveri bank", "country": "in"}
    k1 = make_cache_key("apple_itunes", "search", p1)
    k2 = make_cache_key("apple_itunes", "search", p2)
    assert k1 == k2
    assert len(k1) == 64  # SHA-256 hex length

    # 2. Sensitivity: changing any parameter changes the hash
    k_diff_country = make_cache_key(
        "apple_itunes", "search", {"term": "kaveri bank", "country": "us", "limit": 25}
    )
    assert k_diff_country != k1

    k_diff_limit = make_cache_key(
        "apple_itunes", "search", {"term": "kaveri bank", "country": "in", "limit": 50}
    )
    assert k_diff_limit != k1

    k_diff_term = make_cache_key(
        "apple_itunes", "search", {"term": "other bank", "country": "in", "limit": 25}
    )
    assert k_diff_term != k1

    k_diff_source = make_cache_key("other_source", "search", p1)
    assert k_diff_source != k1

    k_diff_op = make_cache_key("apple_itunes", "lookup", p1)
    assert k_diff_op != k1


def test_in_memory_cache_fake_ttl_and_stale_access() -> None:
    cache = InMemoryCacheFake(default_ttl_s=3600)
    key = "test_key"
    payload = {"results": [{"trackId": 123}]}

    cache.put(key, "apple_itunes", {"term": "test"}, payload)

    # Fresh hit with max_age_s specified
    record = cache.get(key, max_age_s=3600)
    assert record is not None
    assert record.response == payload

    # Expired hit with max_age_s=0
    expired = cache.get(key, max_age_s=0)
    assert expired is None

    # Stale access with max_age_s=None returns entry of any age
    stale = cache.get(key, max_age_s=None)
    assert stale is not None
    assert stale.response == payload

    # Convenience alias get_stale
    assert cache.get_stale(key) is not None

    cache.clear()
    assert cache.get(key, max_age_s=None) is None


@pytest.mark.asyncio
@respx.mock
async def test_apple_fresh_cache_hit_assert_zero_http_calls() -> None:
    fixture_data = json.loads(APPLE_SAMPLE_PATH.read_text(encoding="utf-8"))
    route = respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(200, json=fixture_data)
    )

    cache = InMemoryCacheFake(default_ttl_s=3600)
    adapter = AppleItunesAdapter(cache=cache, min_interval_s=0.0)
    plan = QueryPlan(
        brand_id=uuid4(),
        queries=[PlannedQuery(term="bank", kind="BASE", priority=1)],
    )

    # 1. Miss -> 1 HTTP call, populates cache
    res1 = await adapter.search(plan)
    assert route.call_count == 1
    assert res1.source_mode == SourceMode.LIVE
    assert res1.cache_hit_count == 0
    assert res1.candidates[0].source_mode == SourceMode.LIVE
    orig_time = res1.candidates[0].retrieved_at

    # 2. Fresh hit -> 0 new HTTP calls (call_count remains 1)
    res2 = await adapter.search(plan)
    assert route.call_count == 1  # ZERO new HTTP calls
    assert res2.source_mode == SourceMode.CACHED
    assert res2.cache_hit_count == 1
    assert res2.status == SourceStatus.CONNECTED
    assert len(res2.candidates) == 5

    # Retains original retrieved_at timestamp (never "now")
    cand = res2.candidates[0]
    assert cand.source_mode == SourceMode.CACHED
    assert cand.retrieved_at == orig_time


@pytest.mark.asyncio
@respx.mock
async def test_apple_expired_entry_refetches() -> None:
    fixture_data = json.loads(APPLE_SAMPLE_PATH.read_text(encoding="utf-8"))
    route = respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(200, json=fixture_data)
    )

    cache = InMemoryCacheFake()
    # Configure adapter with ttl_s = 0 so entries immediately expire
    adapter = AppleItunesAdapter(cache=cache, ttl_s=0, min_interval_s=0.0)
    plan = QueryPlan(
        brand_id=uuid4(), queries=[PlannedQuery(term="bank", kind="BASE", priority=1)]
    )

    # First call puts entry
    await adapter.search(plan)
    assert route.call_count == 1

    # Second call detects expired entry and refetches via HTTP
    res2 = await adapter.search(plan)
    assert route.call_count == 2
    assert res2.source_mode == SourceMode.LIVE


@pytest.mark.asyncio
@respx.mock
async def test_apple_force_refresh_bypasses_and_overwrites() -> None:
    data_v1 = {
        "resultCount": 1,
        "results": [{"trackId": 1, "trackName": "V1", "kind": "software"}],
    }
    data_v2 = {
        "resultCount": 1,
        "results": [{"trackId": 1, "trackName": "V2 Overwritten", "kind": "software"}],
    }

    route = respx.get("https://itunes.apple.com/search").mock(
        side_effect=[
            httpx.Response(200, json=data_v1),
            httpx.Response(200, json=data_v2),
        ]
    )

    cache = InMemoryCacheFake(default_ttl_s=3600)
    adapter = AppleItunesAdapter(cache=cache, min_interval_s=0.0)
    plan = QueryPlan(
        brand_id=uuid4(), queries=[PlannedQuery(term="bank", kind="BASE", priority=1)]
    )

    # 1. Normal call
    res1 = await adapter.search(plan)
    assert res1.candidates[0].display_name == "V1"
    assert route.call_count == 1

    # 2. force_refresh=True -> bypasses cache, makes 2nd HTTP call, overwrites cache
    res2 = await adapter.search(plan, force_refresh=True)
    assert route.call_count == 2
    assert res2.source_mode == SourceMode.LIVE
    assert res2.candidates[0].display_name == "V2 Overwritten"

    # 3. Next normal call gets the overwritten V2 from cache with 0 HTTP calls
    res3 = await adapter.search(plan)
    assert route.call_count == 2
    assert res3.source_mode == SourceMode.CACHED
    assert res3.candidates[0].display_name == "V2 Overwritten"


@pytest.mark.asyncio
@respx.mock
async def test_apple_stale_used_only_with_allow_stale_cache_and_labelled_partial() -> (
    None
):
    cached_payload = {
        "resultCount": 1,
        "results": [{"trackId": 99, "trackName": "Stale Bank", "kind": "software"}],
    }
    fixed_time = datetime(2026, 10, 12, 5, 12, 0, tzinfo=UTC)

    cache = InMemoryCacheFake()
    # Pre-populate cache with an older record
    cache_key = make_cache_key(
        "apple_itunes",
        "search",
        {"country": "in", "entity": "software", "limit": 50, "term": "bank"},
    )
    cache._store[cache_key] = CachedResponse(
        key=cache_key,
        source_id="apple_itunes",
        request={},
        response=cached_payload,
        retrieved_at=fixed_time,
    )

    # Provider is now down (503 Service Unavailable)
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(503, text="Service Unavailable")
    )

    adapter = AppleItunesAdapter(
        cache=cache, ttl_s=0, min_interval_s=0.0
    )  # expired entry
    plan = QueryPlan(
        brand_id=uuid4(), queries=[PlannedQuery(term="bank", kind="BASE", priority=1)]
    )

    # 1. Default (allow_stale_cache=False) -> NEVER use stale entries
    res_default = await adapter.search(plan, allow_stale_cache=False)
    assert res_default.status == SourceStatus.ERROR
    assert len(res_default.candidates) == 0
    assert res_default.source_mode is None

    # 2. allow_stale_cache=True -> uses stale entry, marked PARTIAL, message states cache time
    res_stale = await adapter.search(plan, allow_stale_cache=True)
    assert res_stale.status == SourceStatus.PARTIAL
    assert res_stale.source_mode == SourceMode.CACHED
    assert res_stale.error_code == ProviderErrorCode.PROVIDER_UNAVAILABLE
    assert "Showing cached results from 05:12 UTC." in res_stale.message
    assert len(res_stale.candidates) == 1
    assert res_stale.candidates[0].source_mode == SourceMode.CACHED
    assert res_stale.candidates[0].retrieved_at == fixed_time


@pytest.mark.asyncio
@respx.mock
async def test_failure_never_cached() -> None:
    cache = InMemoryCacheFake(default_ttl_s=3600)
    adapter = AppleItunesAdapter(cache=cache, min_interval_s=0.0)
    plan = QueryPlan(
        brand_id=uuid4(),
        queries=[PlannedQuery(term="failterm", kind="BASE", priority=1)],
    )

    # Provider fails 500
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    res = await adapter.search(plan)
    assert res.status == SourceStatus.ERROR

    # Cache must contain zero entries
    assert len(cache._store) == 0


@pytest.mark.asyncio
@respx.mock
async def test_mixed_live_and_cache_run_maintains_correct_modes_and_counts() -> None:
    respx.get("https://itunes.apple.com/search").mock(
        side_effect=[
            # Query 1 live call
            httpx.Response(
                200,
                json={
                    "resultCount": 1,
                    "results": [
                        {"trackId": 10, "trackName": "App 1", "kind": "software"}
                    ],
                },
            ),
            # Query 2 live call
            httpx.Response(
                200,
                json={
                    "resultCount": 1,
                    "results": [
                        {"trackId": 20, "trackName": "App 2", "kind": "software"}
                    ],
                },
            ),
            # On next run, Query 2 is forced or fresh
            httpx.Response(
                200,
                json={
                    "resultCount": 1,
                    "results": [
                        {"trackId": 30, "trackName": "App 3", "kind": "software"}
                    ],
                },
            ),
        ]
    )

    cache = InMemoryCacheFake(default_ttl_s=3600)
    adapter = AppleItunesAdapter(cache=cache, min_interval_s=0.0)

    # Pre-cache only query 1
    p1 = QueryPlan(
        brand_id=uuid4(), queries=[PlannedQuery(term="term1", kind="BASE", priority=1)]
    )
    await adapter.search(p1)

    # Now execute plan with both query 1 (cached) and query 2 (uncached)
    p_mixed = QueryPlan(
        brand_id=uuid4(),
        queries=[
            PlannedQuery(term="term1", kind="BASE", priority=1),
            PlannedQuery(term="term2", kind="ADDED_WORD", priority=2),
        ],
    )
    res_mixed = await adapter.search(p_mixed)

    assert res_mixed.status == SourceStatus.CONNECTED
    assert res_mixed.source_mode == SourceMode.LIVE
    assert res_mixed.cache_hit_count == 1
    assert res_mixed.queries_executed == 2
    assert len(res_mixed.candidates) == 2

    c1 = next(c for c in res_mixed.candidates if c.stable_identifier == "10")
    c2 = next(c for c in res_mixed.candidates if c.stable_identifier == "20")

    assert c1.source_mode == SourceMode.CACHED
    assert c2.source_mode == SourceMode.LIVE


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_discovery_and_enrichment_caching() -> None:
    search_data = json.loads(BSKY_SEARCH_PATH.read_text(encoding="utf-8"))
    profiles_data = json.loads(BSKY_PROFILES_PATH.read_text(encoding="utf-8"))

    search_route = respx.get(
        "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
    ).mock(return_value=httpx.Response(200, json=search_data))
    profile_route = respx.get(
        "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles"
    ).mock(return_value=httpx.Response(200, json=profiles_data))

    cache = InMemoryCacheFake(default_ttl_s=3600)
    adapter = BlueskyPublicAdapter(cache=cache, min_interval_s=0.0)
    plan = QueryPlan(
        brand_id=uuid4(), queries=[PlannedQuery(term="bank", kind="BASE", priority=1)]
    )

    # 1. Miss -> 1 search call, 1 profile call
    res1 = await adapter.search(plan)
    assert search_route.call_count == 1
    assert profile_route.call_count == 1
    assert res1.source_mode == SourceMode.LIVE
    orig_time = res1.candidates[0].retrieved_at

    # 2. Fresh hit -> 0 new calls
    res2 = await adapter.search(plan)
    assert search_route.call_count == 1
    assert profile_route.call_count == 1
    assert res2.source_mode == SourceMode.CACHED
    assert res2.cache_hit_count == 2  # 1 searchActors hit + 1 getProfiles hit
    assert res2.candidates[0].source_mode == SourceMode.CACHED
    assert res2.candidates[0].retrieved_at == orig_time


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_stale_fallback_on_failure() -> None:
    cached_search = {"actors": [{"did": "did:plc:old1", "handle": "old.bsky.social"}]}
    fixed_time = datetime(2026, 10, 12, 5, 12, 0, tzinfo=UTC)

    cache = InMemoryCacheFake()
    cache_key = make_cache_key(
        "bluesky_public", "searchActors", {"limit": 50, "q": "bank"}
    )
    cache._store[cache_key] = CachedResponse(
        key=cache_key,
        source_id="bluesky_public",
        request={},
        response=cached_search,
        retrieved_at=fixed_time,
    )

    # Provider fails with 500
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(500, text="Down")
    )
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(200, json={"profiles": []})
    )

    adapter = BlueskyPublicAdapter(cache=cache, ttl_s=0, min_interval_s=0.0)
    plan = QueryPlan(
        brand_id=uuid4(), queries=[PlannedQuery(term="bank", kind="BASE", priority=1)]
    )

    res = await adapter.search(plan, allow_stale_cache=True)
    assert res.status == SourceStatus.PARTIAL
    assert res.source_mode == SourceMode.CACHED
    assert "Showing cached results from 05:12 UTC." in res.message
    assert len(res.candidates) == 1
    assert res.candidates[0].retrieved_at == fixed_time
