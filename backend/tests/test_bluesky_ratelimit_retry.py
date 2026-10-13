"""Tests for Bluesky rate limit backoff retry, inter-query delay, and partial recovery."""
import time
from uuid import uuid4

import httpx
import pytest
import respx

from app.schemas import PlannedQuery, QueryPlan, SourceStatus
from app.services.sources.bluesky import BlueskyPublicAdapter


@pytest.mark.anyio
@respx.mock
async def test_bluesky_429_exponential_backoff_retry_succeeds() -> None:
    """Ensure HTTP 429 triggers exponential backoff retry and recovers on next attempt."""
    plan = QueryPlan(
        brand_id=uuid4(),
        queries=[PlannedQuery(term="kaveri", kind="BASE", priority=1)],
    )

    mock_search = {
        "actors": [
            {
                "did": "did:plc:kaveri123",
                "handle": "kaveribank.bsky.social",
                "displayName": "Kaveri Bank Official",
            }
        ]
    }
    mock_profiles = {
        "profiles": [
            {
                "did": "did:plc:kaveri123",
                "handle": "kaveribank.bsky.social",
                "displayName": "Kaveri Bank Official",
                "followersCount": 1500,
            }
        ]
    }

    # Simulate 429 on first attempt, 200 on retry
    search_route = respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors")
    search_route.side_effect = [
        httpx.Response(429, text="Rate limit exceeded"),
        httpx.Response(200, json=mock_search),
    ]

    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(200, json=mock_profiles)
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0, rate_limit_retries=1, query_delay_s=0.0)
    result = await adapter.search(plan)

    assert search_route.call_count == 2
    assert result.status == SourceStatus.CONNECTED
    assert len(result.candidates) == 1
    assert result.candidates[0].stable_identifier == "did:plc:kaveri123"


@pytest.mark.anyio
@respx.mock
async def test_bluesky_inter_query_delay_applied() -> None:
    """Ensure delay is introduced between multiple queries to avoid bursts."""
    plan = QueryPlan(
        brand_id=uuid4(),
        queries=[
            PlannedQuery(term="kaveri", kind="BASE", priority=1),
            PlannedQuery(term="kaveribank", kind="BASE", priority=2),
        ],
    )

    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(200, json={"actors": []})
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0, query_delay_s=0.05, rate_limit_retries=0)
    t0 = time.monotonic()
    result = await adapter.search(plan)
    elapsed = time.monotonic() - t0

    assert elapsed >= 0.04
    assert result.status == SourceStatus.CONNECTED


@pytest.mark.anyio
@respx.mock
async def test_bluesky_graceful_partial_results_on_enrichment_429() -> None:
    """Ensure pipeline does not crash when enrichment fails with 429, keeping discovered candidates."""
    plan = QueryPlan(
        brand_id=uuid4(),
        queries=[PlannedQuery(term="kaveri", kind="BASE", priority=1)],
    )

    mock_search = {
        "actors": [
            {
                "did": "did:plc:kaveri999",
                "handle": "kaverisec.bsky.social",
                "displayName": "Kaveri Security",
            }
        ]
    }

    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(200, json=mock_search)
    )
    # Enrichment 429 fails completely
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(429, text="Rate Limited")
    )

    adapter = BlueskyPublicAdapter(min_interval_s=0.0, rate_limit_retries=0, query_delay_s=0.0)
    result = await adapter.search(plan)

    # Outcome reflects PARTIAL / RATE_LIMITED but retains candidates without crashing pipeline
    assert result.status in {SourceStatus.PARTIAL, SourceStatus.RATE_LIMITED}
    assert len(result.candidates) == 1
    assert result.candidates[0].display_name == "Kaveri Security"
