"""Unit and respx mock tests for Bluesky source adapter.

Owner: Person 3 (backend/app/services/sources/tests/test_bluesky_source.py)
Reference: Contract Sections 5.5, 5.6, 12, 13.2, Phase 3 specs
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
from app.services.sources.bluesky import (
    BlueskyPublicAdapter,
    BlueskySourceAdapter,
    is_self_labelled_no_unauth,
    map_bluesky_profile,
    parse_iso_date,
)
from app.services.sources.errors import ProviderError

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "tests" / "fixtures"
BSKY_SEARCH_FIXTURE_PATH = FIXTURES_DIR / "bsky_search_actors_bank.json"
BSKY_PROFILES_FIXTURE_PATH = FIXTURES_DIR / "bsky_get_profiles.json"


@pytest.fixture
def plan() -> QueryPlan:
    return QueryPlan(
        brand_id=uuid4(),
        queries=[
            PlannedQuery(term="bank", kind="BASE", priority=1),
        ],
    )


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_search_success_field_by_field_against_fixture(
    plan: QueryPlan,
) -> None:
    search_data = json.loads(BSKY_SEARCH_FIXTURE_PATH.read_text(encoding="utf-8"))
    profiles_data = json.loads(BSKY_PROFILES_FIXTURE_PATH.read_text(encoding="utf-8"))

    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(200, json=search_data)
    )
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(200, json=profiles_data)
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert result.status == SourceStatus.CONNECTED
    assert result.source_id == "bluesky_public"
    assert result.source_mode == SourceMode.LIVE
    assert result.queries_executed == 1
    assert result.error_code is None
    assert len(result.candidates) == 5

    # Assert field-by-field for the first candidate
    cand = result.candidates[0]
    first_profile = profiles_data["profiles"][0]

    assert cand.source_id == "bluesky_public"
    assert cand.platform == "bluesky"
    assert cand.asset_type == AssetType.SOCIAL_ACCOUNT
    assert cand.stable_identifier == first_profile["did"]
    assert cand.handle == first_profile["handle"]
    assert cand.display_name == first_profile["displayName"]
    assert cand.description == first_profile["description"]
    assert cand.icon_url == first_profile["avatar"]
    assert cand.followers == first_profile["followersCount"]
    assert cand.following == first_profile["followsCount"]
    assert cand.posts_count == first_profile["postsCount"]
    assert cand.canonical_url == f"https://bsky.app/profile/{first_profile['handle']}"
    assert cand.publisher_name is None
    assert cand.developer_id is None
    assert cand.category is None
    assert cand.rating_count is None
    assert cand.source_mode == SourceMode.LIVE
    assert cand.created_at_source == datetime(
        2024, 11, 12, 6, 12, 47, 702000, tzinfo=UTC
    )
    assert cand.matched_queries == ["bank"]


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_search_429_rate_limited(plan: QueryPlan) -> None:
    route = respx.get(
        "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
    ).mock(return_value=httpx.Response(429, text="Rate Limit Exceeded"))

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert route.call_count == 1
    assert result.status == SourceStatus.RATE_LIMITED
    assert result.error_code == ProviderErrorCode.RATE_LIMITED
    assert len(result.candidates) == 0


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_search_403_auth_required(plan: QueryPlan) -> None:
    route = respx.get(
        "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
    ).mock(return_value=httpx.Response(403, text="Auth Required"))

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert route.call_count == 1
    assert result.status == SourceStatus.ERROR
    assert result.error_code == ProviderErrorCode.AUTH_REQUIRED
    assert len(result.candidates) == 0


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_search_5xx_then_success(plan: QueryPlan) -> None:
    search_data = json.loads(BSKY_SEARCH_FIXTURE_PATH.read_text(encoding="utf-8"))
    profiles_data = json.loads(BSKY_PROFILES_FIXTURE_PATH.read_text(encoding="utf-8"))

    route = respx.get(
        "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
    ).mock(
        side_effect=[
            httpx.Response(503, text="Service Unavailable"),
            httpx.Response(200, json=search_data),
        ]
    )
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(200, json=profiles_data)
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert route.call_count == 2
    assert result.status == SourceStatus.CONNECTED
    assert len(result.candidates) == 5


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_search_timeout(plan: QueryPlan) -> None:
    route = respx.get(
        "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
    ).mock(side_effect=httpx.TimeoutException("Timeout"))

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert route.call_count == 2  # 1 retry on timeout
    assert result.status == SourceStatus.ERROR
    assert result.error_code == ProviderErrorCode.TIMEOUT
    assert len(result.candidates) == 0


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_search_invalid_json(plan: QueryPlan) -> None:
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(200, text="<bad_json>")
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert result.status == SourceStatus.ERROR
    assert result.error_code == ProviderErrorCode.INVALID_RESPONSE
    assert len(result.candidates) == 0


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_discovery_ok_enrichment_500_keeps_candidates_with_counts_none(
    plan: QueryPlan,
) -> None:
    search_data = {
        "actors": [
            {
                "did": "did:plc:test1234",
                "handle": "testbank.bsky.social",
                "displayName": "Test Bank",
                "description": "Welcome to test bank",
                "labels": [],
            }
        ]
    }
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(200, json=search_data)
    )
    # getProfiles fails with 500
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(500, text="Enrichment Error")
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    # Must keep candidates, mark outcome PARTIAL, and counts must be None (never 0)
    assert result.status == SourceStatus.PARTIAL
    assert result.error_code == ProviderErrorCode.PROVIDER_UNAVAILABLE
    assert len(result.candidates) == 1
    cand = result.candidates[0]
    assert cand.stable_identifier == "did:plc:test1234"
    assert cand.followers is None
    assert cand.following is None
    assert cand.posts_count is None


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_self_labelled_account_skipped_and_counted(
    plan: QueryPlan,
) -> None:
    search_data = {
        "actors": [
            {
                "did": "did:plc:public1",
                "handle": "public.bsky.social",
                "displayName": "Public Account",
                "labels": [],
            },
            {
                "did": "did:plc:private2",
                "handle": "private.bsky.social",
                "displayName": "Private Account",
                "labels": [{"val": "!no-unauthenticated", "src": "did:plc:private2"}],
            },
        ]
    }
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(200, json=search_data)
    )
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(
            200,
            json={
                "profiles": [{"did": "did:plc:public1", "handle": "public.bsky.social"}]
            },
        )
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert len(result.candidates) == 1
    assert result.candidates[0].stable_identifier == "did:plc:public1"
    assert (
        "1 accounts skipped (asked not to be shown to logged-out users)."
        in result.message
    )


def test_bluesky_display_name_empty_falls_back_to_handle_and_did() -> None:
    item_empty_display = {
        "did": "did:plc:sample1",
        "handle": "sample.bsky.social",
        "displayName": "",
    }
    cand1 = map_bluesky_profile(item_empty_display)
    assert cand1.display_name == "sample.bsky.social"

    item_none_display = {
        "did": "did:plc:sample2",
        "handle": "sample2.bsky.social",
        "displayName": None,
    }
    cand2 = map_bluesky_profile(item_none_display)
    assert cand2.display_name == "sample2.bsky.social"

    item_invalid_handle = {
        "did": "did:plc:sample3",
        "handle": "handle.invalid",
        "displayName": "",
    }
    cand3 = map_bluesky_profile(item_invalid_handle)
    assert cand3.handle is None
    assert cand3.display_name == "did:plc:sample3"


def test_bluesky_links_from_bio_and_website() -> None:
    item = {
        "did": "did:plc:linktest",
        "handle": "linktest.bsky.social",
        "description": "Visit HTTP://WWW.EXAMPLE.COM/page., or ftp://ignore and (http://www.example.com/page)",
        "website": "https://company.example/portal!",
    }
    cand = map_bluesky_profile(item)
    # Deduplicated, lowercase host, trailing punctuation trimmed, http/https only
    assert "http://www.example.com/page" in cand.external_links
    assert "https://company.example/portal" in cand.external_links
    assert len(cand.external_links) == 2


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_enrichment_batch_splitting_25() -> None:
    # 30 unique DIDs
    actors = [
        {"did": f"did:plc:actor{i}", "handle": f"actor{i}.bsky.social"}
        for i in range(30)
    ]
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(200, json={"actors": actors})
    )
    profile_route = respx.get(
        "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles"
    ).mock(
        side_effect=[
            httpx.Response(200, json={"profiles": actors[:25]}),
            httpx.Response(200, json={"profiles": actors[25:]}),
        ]
    )

    p = QueryPlan(
        brand_id=uuid4(),
        queries=[PlannedQuery(term="actors", kind="BASE", priority=1)],
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    result = await adapter.search(p)

    assert len(result.candidates) == 30
    # 30 DIDs split into batch of 25 and batch of 5 -> 2 calls
    assert profile_route.call_count == 2
    # First batch requested 25 actors
    call1_actors = profile_route.calls[0].request.url.params.get_list("actors")
    assert len(call1_actors) == 25
    # Second batch requested 5 actors
    call2_actors = profile_route.calls[1].request.url.params.get_list("actors")
    assert len(call2_actors) == 5


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_dedupe_across_queries_and_cap_at_50() -> None:
    p = QueryPlan(
        brand_id=uuid4(),
        queries=[
            PlannedQuery(term="term1", kind="BASE", priority=1),
            PlannedQuery(term="term2", kind="ADDED_WORD", priority=2),
        ],
    )

    # 60 distinct accounts
    batch1 = [
        {"did": f"did:plc:user{i}", "handle": f"user{i}.bsky.social"} for i in range(40)
    ]
    batch2 = [
        {"did": f"did:plc:user{i}", "handle": f"user{i}.bsky.social"}
        for i in range(20, 60)
    ]

    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        side_effect=[
            httpx.Response(200, json={"actors": batch1}),
            httpx.Response(200, json={"actors": batch2}),
        ]
    )
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(200, json={"profiles": []})
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    result = await adapter.search(p)

    # Capped at 50 accounts
    assert len(result.candidates) == 50

    # User 20 appeared in both queries
    user20 = next(
        c for c in result.candidates if c.stable_identifier == "did:plc:user20"
    )
    assert user20.matched_queries == ["term1", "term2"]


def test_bluesky_handle_invalid_sanitization() -> None:
    item = {
        "did": "did:plc:corrupt1",
        "handle": "handle.invalid",
        "displayName": "Corrupt User",
    }
    cand = map_bluesky_profile(item)
    assert cand.handle is None
    assert cand.canonical_url == "https://bsky.app/profile/did:plc:corrupt1"


def test_bluesky_cyrillic_display_name_preserved_byte_for_byte() -> None:
    cyrillic_i = "\u0456"
    raw_name = f"Kaver{cyrillic_i} Official"
    item = {
        "did": "did:plc:cyrillic",
        "handle": "kaveri.bsky.social",
        "displayName": raw_name,
    }
    cand = map_bluesky_profile(item)
    assert cand.display_name == raw_name
    assert cand.display_name[5] == "\u0456"


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_search_no_simulated_mode(plan: QueryPlan) -> None:
    search_data = json.loads(BSKY_SEARCH_FIXTURE_PATH.read_text(encoding="utf-8"))
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(200, json=search_data)
    )
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(200, json={"profiles": []})
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    result = await adapter.search(plan)

    assert result.source_mode != SourceMode.SIMULATED
    assert result.source_mode == SourceMode.LIVE
    for c in result.candidates:
        assert c.source_mode != SourceMode.SIMULATED


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_mid_scan_429_partial_semantics() -> None:
    p = QueryPlan(
        brand_id=uuid4(),
        queries=[
            PlannedQuery(term="q1", kind="BASE", priority=1),
            PlannedQuery(term="q2", kind="ADDED_WORD", priority=2),
        ],
    )

    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "actors": [{"did": "did:plc:q1user", "handle": "q1.bsky.social"}]
                },
            ),
            httpx.Response(429, text="Rate limit"),
        ]
    )
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(
            200,
            json={"profiles": [{"did": "did:plc:q1user", "handle": "q1.bsky.social"}]},
        )
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    result = await adapter.search(p)

    assert result.status == SourceStatus.RATE_LIMITED
    assert result.error_code == ProviderErrorCode.RATE_LIMITED
    assert len(result.candidates) == 1
    assert "Stopped after 1 of 2 queries; partial results kept." in result.message


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_lookup_by_did_and_handle() -> None:
    profiles_data = json.loads(BSKY_PROFILES_FIXTURE_PATH.read_text(encoding="utf-8"))
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(200, json=profiles_data)
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)

    # 1. Lookup by DID
    cand1 = await adapter.lookup("did:plc:5klap434eteydsxvdydtqkf2")
    assert cand1 is not None
    assert cand1.stable_identifier == "did:plc:5klap434eteydsxvdydtqkf2"

    # 2. Lookup by handle
    cand2 = await adapter.lookup("jillwine-banks.bsky.social")
    assert cand2 is not None
    assert cand2.handle == "jillwine-banks.bsky.social"

    # 3. Lookup by valid bsky.app URL
    cand3 = await adapter.lookup("https://bsky.app/profile/jillwine-banks.bsky.social")
    assert cand3 is not None

    # 4. Lookup invalid inputs return None
    assert await adapter.lookup("https://evil.example/profile/123") is None
    assert await adapter.lookup("invalid handle without dot") is None
    assert await adapter.lookup("bad@handle") is None


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_health_check_session_tracking() -> None:
    adapter = BlueskyPublicAdapter(min_interval_s=0.0)

    # 1. Initial health check: reports CONNECTED, "No request made yet.", last_checked_at=None
    h0 = await adapter.health_check()
    assert h0.status == SourceStatus.CONNECTED
    assert h0.message == "No request made yet."
    assert h0.last_checked_at is None
    assert h0.rate_limit_note == "Conservative: about 1 request per second"

    # 2. After live search: reports last real outcome
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(200, json={"actors": []})
    )
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(200, json={"profiles": []})
    )
    p = QueryPlan(
        brand_id=uuid4(),
        queries=[PlannedQuery(term="bank", kind="BASE", priority=1)],
    )
    await adapter.search(p)

    h1 = await adapter.health_check()
    assert h1.status == SourceStatus.CONNECTED
    assert h1.message == "Live public profile search and enrichment available."
    assert h1.last_checked_at is not None

    # 3. Force refresh: performs minimal live call
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(429, text="Rate limit")
    )
    h2 = await adapter.health_check(force_refresh=True)
    assert h2.status == SourceStatus.RATE_LIMITED
    assert h2.message == "Provider rate limit active."


@pytest.mark.asyncio
@respx.mock
async def test_bluesky_lookup_provider_failure_raises_provider_error() -> None:
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(429, text="Rate limit")
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0)
    with pytest.raises(ProviderError) as exc_info:
        await adapter.lookup("kaveribank.bsky.social")

    assert exc_info.value.error_code == ProviderErrorCode.RATE_LIMITED


def test_bluesky_helpers_and_adapter_alias() -> None:
    assert BlueskySourceAdapter is BlueskyPublicAdapter

    # is_self_labelled_no_unauth
    assert (
        is_self_labelled_no_unauth(
            {
                "did": "did:plc:1",
                "labels": [{"val": "!no-unauthenticated", "src": "did:plc:1"}],
            }
        )
        is True
    )
    assert (
        is_self_labelled_no_unauth(
            {"did": "did:plc:1", "labels": [{"val": "other-label"}]}
        )
        is False
    )

    # parse_iso_date
    assert parse_iso_date("2024-11-12T06:12:47.702Z") == datetime(
        2024, 11, 12, 6, 12, 47, 702000, tzinfo=UTC
    )
    assert parse_iso_date("invalid") is None
