"""Hardening tests: Isolation, honesty, and end-to-end cache fallback (Sections E and F).

Owner: Person 3
Reference: Contract Sections 5.3, 5.5, 12, 15.3, Phase 9 Hardening
"""

from __future__ import annotations

import logging
import socket
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import respx
from app.schemas import (
    PlannedQuery,
    QueryPlan,
    SourceMode,
    SourceStatus,
)
from app.services.sources.apple import AppleItunesAdapter
from app.services.sources.bluesky import BlueskyPublicAdapter
from app.services.sources.cache import InMemoryCacheFake, make_cache_key
from app.services.sources.fixtures_demo import DemoFixtureAdapter
from app.services.sources.fixtures_recorded import RecordedFixtureAdapter
from app.services.sources.ratelimit import AsyncRateLimiter


class TestIsolationAndHonesty:
    """Tests for Sections E and F."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_live_adapters_never_emit_simulated(self) -> None:
        # Mock Apple response
        respx.get("https://itunes.apple.com/search").respond(
            200,
            json={
                "resultCount": 1,
                "results": [
                    {
                        "trackId": 12345,
                        "trackName": "Kaveri Live",
                        "bundleId": "com.kaveri.live",
                        "sellerName": "Kaveri Bank",
                        "kind": "software",
                    }
                ],
            },
        )
        apple = AppleItunesAdapter(rate_limiter=AsyncRateLimiter(0.0))
        plan = QueryPlan(
            brand_id=uuid4(),
            queries=[PlannedQuery(term="kaveri", kind="EXACT", priority=1)],
        )
        res_apple = await apple.search(plan)

        assert res_apple.source_mode != SourceMode.SIMULATED
        assert res_apple.source_mode == SourceMode.LIVE
        assert all(c.source_mode != SourceMode.SIMULATED for c in res_apple.candidates)

        # Mock Bluesky response
        respx.get(
            "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
        ).respond(
            200,
            json={
                "actors": [{"did": "did:plc:kaveri", "handle": "kaveri.bsky.social"}]
            },
        )
        respx.get(
            "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles"
        ).respond(
            200,
            json={
                "profiles": [{"did": "did:plc:kaveri", "handle": "kaveri.bsky.social"}]
            },
        )
        bsky = BlueskyPublicAdapter(rate_limiter=AsyncRateLimiter(0.0))
        res_bsky = await bsky.search(plan)

        assert res_bsky.source_mode != SourceMode.SIMULATED
        assert res_bsky.source_mode == SourceMode.LIVE
        assert all(c.source_mode != SourceMode.SIMULATED for c in res_bsky.candidates)

    @pytest.mark.asyncio
    async def test_demo_and_recorded_adapters_never_touch_network(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def forbidden_connect(*args, **kwargs):
            raise RuntimeError("NETWORK ACCESS STRICTLY FORBIDDEN IN FIXTURE ADAPTERS")

        monkeypatch.setattr(socket.socket, "connect", forbidden_connect)

        # Demo adapter
        demo = DemoFixtureAdapter()
        plan = QueryPlan(
            brand_id=uuid4(),
            queries=[PlannedQuery(term="kaveri", kind="EXACT", priority=1)],
        )
        res_demo = await demo.search(plan)
        assert res_demo.source_mode == SourceMode.SIMULATED
        assert res_demo.status == SourceStatus.CONNECTED
        assert len(res_demo.candidates) > 0

        # Recorded adapter
        rec = RecordedFixtureAdapter()
        res_rec = await rec.search(plan)
        assert res_rec.source_mode == SourceMode.CACHED
        assert res_rec.status == SourceStatus.CONNECTED

    @pytest.mark.asyncio
    @respx.mock
    async def test_logs_and_exceptions_never_leak_payload_bodies_tokens_or_query_strings(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        secret_token = "Bearer secret_jwt_token_12345"
        sensitive_payload = '{"secret_payload": "confidential_credit_card_data"}'

        respx.get("https://itunes.apple.com/search").respond(
            500,
            text=sensitive_payload,
            headers={"Authorization": secret_token},
        )

        adapter = AppleItunesAdapter(rate_limiter=AsyncRateLimiter(0.0))
        plan = QueryPlan(
            brand_id=uuid4(),
            queries=[PlannedQuery(term="secretqueryterms", kind="EXACT", priority=1)],
        )

        with caplog.at_level(logging.DEBUG):
            res = await adapter.search(plan)

        # Assert no payload body in message or logs
        assert "confidential_credit_card_data" not in res.message
        assert "confidential_credit_card_data" not in caplog.text

        # Assert no tokens in message or logs
        assert "secret_jwt_token_12345" not in res.message
        assert "secret_jwt_token_12345" not in caplog.text

        # Assert no raw URL with query string in message
        assert "?term=" not in res.message
        assert "&country=" not in res.message

    @pytest.mark.asyncio
    @respx.mock
    async def test_messages_follow_copy_guide_no_forbidden_phrases(self) -> None:
        # Failure case
        respx.get("https://itunes.apple.com/search").respond(503, text="Unavailable")
        adapter = AppleItunesAdapter(rate_limiter=AsyncRateLimiter(0.0))
        plan = QueryPlan(
            brand_id=uuid4(),
            queries=[PlannedQuery(term="test", kind="EXACT", priority=1)],
        )
        res_fail = await adapter.search(plan)

        msg_fail = res_fail.message.lower()
        assert "0 results" not in msg_fail
        assert "all clear" not in msg_fail
        assert "safe" not in msg_fail
        assert "no threats" not in msg_fail

        # Empty result case
        respx.get("https://itunes.apple.com/search").respond(
            200, json={"resultCount": 0, "results": []}
        )
        res_empty = await adapter.search(plan)
        msg_empty = res_empty.message.lower()
        assert "0 results" not in msg_empty
        assert "all clear" not in msg_empty
        assert "safe" not in msg_empty

    @pytest.mark.asyncio
    @respx.mock
    async def test_cache_fallback_end_to_end_scenario(self) -> None:
        # Scenario test (Section F):
        # 1. Past successful scan cached candidates at 05:15 UTC
        past_time = datetime(2026, 10, 12, 5, 15, 0, tzinfo=UTC)
        cache = InMemoryCacheFake()

        cached_apple_data = {
            "resultCount": 1,
            "results": [
                {
                    "trackId": 887766,
                    "trackName": "Kaveri Stale App",
                    "bundleId": "com.kaveri.stale",
                    "sellerName": "Kaveri Bank",
                    "kind": "software",
                }
            ],
        }
        req_params = {
            "country": "in",
            "entity": "software",
            "limit": 50,
            "term": "kaveri",
        }
        cache_key = make_cache_key("apple_itunes", "search", req_params)
        cache.put(
            cache_key,
            "apple_itunes",
            req_params,
            cached_apple_data,
            retrieved_at=past_time,
        )

        # 2. TTL is 3600 s. We now run at current time (cache is stale)
        # 3. Live call fails mid-scan with 503
        respx.get("https://itunes.apple.com/search").respond(
            503, text="Service Unavailable"
        )

        adapter = AppleItunesAdapter(
            cache=cache,
            ttl_s=3600,
            rate_limiter=AsyncRateLimiter(0.0),
        )
        plan = QueryPlan(
            brand_id=uuid4(),
            queries=[PlannedQuery(term="kaveri", kind="EXACT", priority=1)],
        )

        # Search with allow_stale_cache=True
        res = await adapter.search(plan, allow_stale_cache=True)

        assert res.status == SourceStatus.PARTIAL
        assert res.source_mode == SourceMode.CACHED
        assert res.queries_executed == 1
        assert res.cache_hit_count == 1
        assert res.error_code is not None
        # Message has cache time
        assert "05:15 UTC" in res.message
        assert len(res.candidates) == 1
        cand = res.candidates[0]
        assert cand.display_name == "Kaveri Stale App"
        assert cand.source_mode == SourceMode.CACHED
        assert cand.retrieved_at == past_time
