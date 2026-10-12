"""Unit and respx mock tests for Apple App Store source adapter.

Owner: Person 3 (backend/app/services/sources/tests/test_apple_source.py)
Reference: Contract Sections 5.5, 5.6, 12, 13.1, Phase 2 specs
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
    AssetType,
    PlannedQuery,
    ProviderErrorCode,
    QueryPlan,
    SourceMode,
    SourceStatus,
)
from app.services.sources.apple import (
    AppleItunesAdapter,
    AppleSourceAdapter,
    map_apple_item,
    parse_apple_date,
)
from app.services.sources.cache import InMemoryCacheRepo
from app.services.sources.errors import ProviderError

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "tests" / "fixtures"
REAL_SAMPLE_PATH = FIXTURES_DIR / "apple_search_bank_sample.json"
REAL_EMPTY_PATH = FIXTURES_DIR / "apple_search_kaveri_bank.json"
REAL_LOOKUP_PATH = FIXTURES_DIR / "apple_lookup_bundle.json"


@pytest.fixture
def plan() -> QueryPlan:
    return QueryPlan(
        brand_id=uuid4(),
        queries=[
            PlannedQuery(term="kaveri bank", kind="BASE", priority=1),
            PlannedQuery(term="kaveri bank rewards", kind="ADDED_WORD", priority=2),
        ],
    )


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_success_field_by_field_against_fixture(
    plan: QueryPlan,
) -> None:
    fixture_data = json.loads(REAL_SAMPLE_PATH.read_text(encoding="utf-8"))
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(200, json=fixture_data)
    )

    adapter = AppleItunesAdapter(country="in", min_interval_s=0.0)
    result = await adapter.search(plan, limit=25)

    assert result.status == SourceStatus.CONNECTED
    assert result.source_id == "apple_itunes"
    assert result.source_mode == SourceMode.LIVE
    assert result.queries_executed == 2
    assert result.error_code is None
    assert result.message == "2 queries completed."
    assert len(result.candidates) == 5

    # Field-by-field assertion against the first result
    first_item = fixture_data["results"][0]
    cand = result.candidates[0]

    assert cand.source_id == "apple_itunes"
    assert cand.platform == "apple_app_store"
    assert cand.asset_type == AssetType.IOS_APP
    assert cand.stable_identifier == str(first_item["trackId"])
    assert cand.secondary_identifiers["bundle_id"] == first_item["bundleId"]
    assert cand.display_name == first_item["trackName"]
    assert cand.publisher_name == first_item["sellerName"]
    assert cand.developer_id == str(first_item["artistId"])
    assert cand.category == first_item["primaryGenreName"]
    assert cand.description == first_item["description"]
    assert cand.icon_url == first_item["artworkUrl512"]
    assert cand.canonical_url == first_item["trackViewUrl"]
    assert cand.created_at_source == datetime(2020, 12, 7, 8, 0, 0, tzinfo=UTC)
    assert cand.rating_count == first_item.get("userRatingCount")
    assert cand.followers is None
    assert cand.following is None
    assert cand.posts_count is None
    assert cand.handle is None
    assert cand.icon_hash is None
    assert cand.source_mode == SourceMode.LIVE
    assert isinstance(cand.retrieved_at, datetime)
    assert "kaveri bank" in cand.matched_queries
    assert "kaveri bank rewards" in cand.matched_queries


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_429_rate_limited_exactly_one_call(plan: QueryPlan) -> None:
    route = respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(429, text="Too Many Requests")
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    result = await adapter.search(plan, limit=10)

    # 429 makes exactly 1 call (never retried, stops remaining queries)
    assert route.call_count == 1
    assert result.status == SourceStatus.RATE_LIMITED
    assert result.error_code == ProviderErrorCode.RATE_LIMITED
    assert len(result.candidates) == 0
    assert result.source_mode is None
    assert result.status != SourceStatus.CONNECTED


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_403_auth_required(plan: QueryPlan) -> None:
    route = respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(403, text="Forbidden")
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert route.call_count == 1
    assert result.status == SourceStatus.ERROR
    assert result.error_code == ProviderErrorCode.AUTH_REQUIRED
    assert len(result.candidates) == 0


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_5xx_retries_once(plan: QueryPlan) -> None:
    route = respx.get("https://itunes.apple.com/search").mock(
        side_effect=[
            httpx.Response(502, text="Bad Gateway"),
            httpx.Response(
                200,
                json={
                    "resultCount": 1,
                    "results": [
                        {"trackId": 123, "trackName": "App 1", "kind": "software"}
                    ],
                },
            ),
            httpx.Response(
                200,
                json={
                    "resultCount": 1,
                    "results": [
                        {"trackId": 123, "trackName": "App 1", "kind": "software"}
                    ],
                },
            ),
        ]
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert route.call_count == 3  # 1 retry on query 1 + 1 attempt on query 2
    assert result.status == SourceStatus.CONNECTED
    assert len(result.candidates) == 1


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_timeout_handling(plan: QueryPlan) -> None:
    route = respx.get("https://itunes.apple.com/search").mock(
        side_effect=httpx.TimeoutException("Connection timed out")
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    # 1 retry per query for 2 planned queries = 4 calls
    assert route.call_count == 4
    assert result.status == SourceStatus.ERROR
    assert result.error_code == ProviderErrorCode.TIMEOUT
    assert len(result.candidates) == 0
    assert "0 results" not in result.message.lower()


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_invalid_json(plan: QueryPlan) -> None:
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(200, text="NOT_VALID_JSON")
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert result.status == SourceStatus.ERROR
    assert result.error_code == ProviderErrorCode.INVALID_RESPONSE
    assert len(result.candidates) == 0


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_mid_scan_429_keeps_earlier_candidates(
    plan: QueryPlan,
) -> None:
    respx.get("https://itunes.apple.com/search").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "resultCount": 1,
                    "results": [
                        {"trackId": 999, "trackName": "Partial App", "kind": "software"}
                    ],
                },
            ),
            httpx.Response(429, text="Too Many Requests"),
        ]
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert result.status == SourceStatus.RATE_LIMITED
    assert result.error_code == ProviderErrorCode.RATE_LIMITED
    assert len(result.candidates) == 1
    assert result.candidates[0].stable_identifier == "999"
    assert "Stopped after 1 of 2 queries; partial results kept." in result.message


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_empty_but_valid_results(plan: QueryPlan) -> None:
    empty_data = json.loads(REAL_EMPTY_PATH.read_text(encoding="utf-8"))
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(200, json=empty_data)
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert result.status == SourceStatus.CONNECTED
    assert result.error_code is None
    assert len(result.candidates) == 0
    assert result.message == "2 queries completed; no matching results returned."


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_malformed_item_skipped(plan: QueryPlan) -> None:
    # Contains a malformed item (missing trackName), a non-software item, and a valid item
    payload = {
        "resultCount": 3,
        "results": [
            {"trackId": 111},  # missing trackName
            {
                "trackId": 222,
                "trackName": "Song",
                "kind": "song",
                "wrapperType": "track",
            },  # not software
            {"trackId": 333, "trackName": "Valid App", "kind": "software"},  # valid
        ],
    }
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(200, json=payload)
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert result.status == SourceStatus.CONNECTED
    assert len(result.candidates) == 1
    assert result.candidates[0].stable_identifier == "333"


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_query_clipped_to_100() -> None:
    long_term = "bank " + ("extra" * 30)  # > 150 chars
    p = QueryPlan(
        brand_id=uuid4(),
        queries=[PlannedQuery(term=long_term, kind="BASE", priority=1)],
    )

    route = respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(200, json={"resultCount": 0, "results": []})
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    await adapter.search(p)

    requested_term = route.calls[0].request.url.params["term"]
    assert len(requested_term) <= 100


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_results_capped_at_50(plan: QueryPlan) -> None:
    many_items = [
        {"trackId": i, "trackName": f"App {i}", "kind": "software"}
        for i in range(1, 65)
    ]
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(
            200, json={"resultCount": len(many_items), "results": many_items}
        )
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    result = await adapter.search(plan, limit=60)

    assert len(result.candidates) == 50


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_duplicate_track_id_merged_with_matched_queries(
    plan: QueryPlan,
) -> None:
    # Query 1 and Query 2 both return trackId 100
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "resultCount": 1,
                "results": [
                    {"trackId": 100, "trackName": "Shared App", "kind": "software"}
                ],
            },
        )
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert len(result.candidates) == 1
    c = result.candidates[0]
    assert c.stable_identifier == "100"
    assert c.matched_queries == ["kaveri bank", "kaveri bank rewards"]


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_country_param_honoured(plan: QueryPlan) -> None:
    route = respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(200, json={"resultCount": 0, "results": []})
    )

    adapter = AppleItunesAdapter(country="gb", min_interval_s=0.0)
    await adapter.search(plan)

    assert route.calls[0].request.url.params["country"] == "gb"


def test_apple_unicode_cyrillic_name_preserved_exactly() -> None:
    # Cyrillic 'і' U+0456
    cyrillic_i = "\u0456"
    raw_name = f"Kaver{cyrillic_i} Mobile App"
    item = {
        "trackId": 777,
        "trackName": raw_name,
        "sellerName": f"Kaver{cyrillic_i} Publisher",
        "kind": "software",
    }

    cand = map_apple_item(item, source_mode=SourceMode.LIVE)
    assert cand.display_name == raw_name
    assert cand.display_name[5] == "\u0456"
    assert cand.publisher_name == f"Kaver{cyrillic_i} Publisher"


def test_apple_release_date_parsing() -> None:
    valid_utc = parse_apple_date("2026-09-25T05:37:13Z")
    assert valid_utc == datetime(2026, 9, 25, 5, 37, 13, tzinfo=UTC)

    invalid_date = parse_apple_date("not-a-date")
    assert invalid_date is None

    empty_date = parse_apple_date(None)
    assert empty_date is None


@pytest.mark.asyncio
@respx.mock
async def test_apple_search_no_simulated_mode_ever_produced(plan: QueryPlan) -> None:
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "resultCount": 1,
                "results": [
                    {"trackId": 555, "trackName": "Real App", "kind": "software"}
                ],
            },
        )
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert result.source_mode != SourceMode.SIMULATED
    assert result.source_mode == SourceMode.LIVE
    for c in result.candidates:
        assert c.source_mode != SourceMode.SIMULATED
        assert c.source_mode == SourceMode.LIVE


@pytest.mark.asyncio
@respx.mock
async def test_apple_lookup_by_id_and_bundle_id() -> None:
    lookup_fixture = json.loads(REAL_LOOKUP_PATH.read_text(encoding="utf-8"))
    route = respx.get("https://itunes.apple.com/lookup").mock(
        return_value=httpx.Response(200, json=lookup_fixture)
    )

    adapter = AppleItunesAdapter(country="in", min_interval_s=0.0)

    # 1. Lookup by digits trackId
    cand1 = await adapter.lookup("1521443352")
    assert cand1 is not None
    assert cand1.stable_identifier == "1521443352"
    assert route.calls[0].request.url.params["id"] == "1521443352"

    # 2. Lookup by bundleId
    cand2 = await adapter.lookup("com.idfcfirstbank.optimus")
    assert cand2 is not None
    assert cand2.secondary_identifiers["bundle_id"] == "com.idfcfirstbank.optimus"
    assert route.calls[1].request.url.params["bundleId"] == "com.idfcfirstbank.optimus"

    # 3. Lookup by valid Apple App Store URL
    cand3 = await adapter.lookup(
        "https://apps.apple.com/in/app/idfc-first-bank/id1521443352"
    )
    assert cand3 is not None
    assert cand3.stable_identifier == "1521443352"


@pytest.mark.asyncio
async def test_apple_lookup_invalid_input_returns_none() -> None:
    adapter = AppleItunesAdapter(min_interval_s=0.0)

    # SSRF / non-store URL
    assert await adapter.lookup("https://evil-apple.example/app/id12345") is None
    assert await adapter.lookup("http://apps.apple.com/in/app/id12345") is None
    assert await adapter.lookup("https://google.com") is None
    assert await adapter.lookup("invalid!@#bundle") is None
    assert await adapter.lookup("a" * 200) is None


@pytest.mark.asyncio
@respx.mock
async def test_apple_lookup_provider_failure_raises_provider_error() -> None:
    respx.get("https://itunes.apple.com/lookup").mock(
        return_value=httpx.Response(429, text="Rate Limited")
    )

    adapter = AppleItunesAdapter(min_interval_s=0.0)
    with pytest.raises(ProviderError) as exc_info:
        await adapter.lookup("com.kbrewards.app")

    assert exc_info.value.error_code == ProviderErrorCode.RATE_LIMITED


@pytest.mark.asyncio
@respx.mock
async def test_apple_health_check_session_tracking() -> None:
    adapter = AppleItunesAdapter(country="in", min_interval_s=0.0)

    # 1. Before requests: reports default CONNECTED with "No request made yet." and last_checked_at=None
    h0 = await adapter.health_check()
    assert h0.status == SourceStatus.CONNECTED
    assert h0.message == "No request made yet."
    assert h0.last_checked_at is None
    assert h0.rate_limit_note == "About 20 requests per minute"

    # 2. After successful live search: reports last real outcome
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(200, json={"resultCount": 0, "results": []})
    )
    p = QueryPlan(
        brand_id=uuid4(),
        queries=[PlannedQuery(term="bank", kind="BASE", priority=1)],
    )
    await adapter.search(p)

    h1 = await adapter.health_check()
    assert h1.status == SourceStatus.CONNECTED
    assert h1.message == "Live catalog search available."
    assert h1.last_checked_at is not None

    # 3. Force refresh minimal check
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(429, text="Rate limit")
    )
    h2 = await adapter.health_check(force_refresh=True)
    assert h2.status == SourceStatus.RATE_LIMITED
    assert h2.message == "Provider rate limit active."


@pytest.mark.asyncio
@respx.mock
async def test_apple_caching_and_stale_fallback(plan: QueryPlan) -> None:
    cache = InMemoryCacheRepo(default_ttl_s=3600)
    adapter = AppleSourceAdapter(cache=cache, min_interval_s=0.0)

    # First call: populates cache
    route = respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "resultCount": 1,
                "results": [
                    {"trackId": 987, "trackName": "Cached App", "kind": "software"}
                ],
            },
        )
    )
    res1 = await adapter.search(plan)
    assert res1.queries_executed == 2
    assert res1.cache_hit_count == 0

    # Second call: served from cache
    res2 = await adapter.search(plan)
    assert res2.queries_executed == 2
    assert res2.cache_hit_count == 2
    assert res2.source_mode == SourceMode.CACHED
    assert len(res2.candidates) == 1

    # Third call with force_refresh=True: bypasses cache
    res3 = await adapter.search(plan, force_refresh=True)
    assert res3.queries_executed == 2
    assert res3.cache_hit_count == 0

    # Fourth call with provider failing and allow_stale_cache=True
    route.mock(return_value=httpx.Response(500, text="Internal Server Error"))
    cache._default_ttl_s = 0  # expire immediately
    res4 = await adapter.search(plan, allow_stale_cache=True)
    assert res4.status == SourceStatus.CONNECTED or res4.status == SourceStatus.PARTIAL
    assert res4.source_mode == SourceMode.CACHED
    assert len(res4.candidates) == 1
