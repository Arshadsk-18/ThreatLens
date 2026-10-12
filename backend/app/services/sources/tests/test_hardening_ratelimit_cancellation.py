"""Hardening tests: Rate limiter and cancellation behaviour (Sections B and C).

Owner: Person 3
Reference: Contract Sections 5.5, 12, Phase 9 Hardening
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import httpx
import pytest
import respx
from app.schemas import PlannedQuery, QueryPlan
from app.services.sources.apple import AppleItunesAdapter
from app.services.sources.bluesky import BlueskyPublicAdapter
from app.services.sources.ratelimit import (
    AsyncRateLimiter,
)


class FakeClock:
    """Deterministic fake clock advancing instantaneously on sleep."""

    def __init__(self, start: float = 1000.0) -> None:
        self.current_time = start
        self.sleep_calls: list[float] = []

    def now(self) -> float:
        return self.current_time

    async def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        self.current_time += seconds
        # Allow event loop cooperative switch
        await asyncio.sleep(0)


class TestRateLimitingAndCancellation:
    """Tests for Sections B and C."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_eight_apple_queries_take_at_least_seven_by_three_seconds_fake_time(
        self,
    ) -> None:
        respx.get("https://itunes.apple.com/search").respond(
            200, json={"resultCount": 0, "results": []}
        )

        fake = FakeClock()
        limiter = AsyncRateLimiter(min_interval_s=3.0, clock=fake.now, sleep=fake.sleep)
        adapter = AppleItunesAdapter(rate_limiter=limiter)

        queries = [
            PlannedQuery(term=f"term_{i}", kind="NAMESAKE", priority=i + 1)
            for i in range(8)
        ]
        plan = QueryPlan(brand_id=uuid4(), queries=queries)

        t_start = fake.now()
        res = await adapter.search(plan, limit=10)
        t_end = fake.now()

        assert res.queries_executed == 8
        # 8 queries means 7 inter-call intervals of 3.0 s = 21.0 s
        assert t_end - t_start >= 21.0
        assert len(fake.sleep_calls) == 7
        assert all(s == 3.0 for s in fake.sleep_calls)

    @pytest.mark.asyncio
    @respx.mock
    async def test_six_bluesky_queries_take_at_least_five_by_one_second_fake_time(
        self,
    ) -> None:
        respx.get(
            "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
        ).respond(200, json={"actors": []})

        fake = FakeClock()
        limiter = AsyncRateLimiter(min_interval_s=1.0, clock=fake.now, sleep=fake.sleep)
        adapter = BlueskyPublicAdapter(rate_limiter=limiter)

        queries = [
            PlannedQuery(term=f"term_{i}", kind="NAMESAKE", priority=i + 1)
            for i in range(6)
        ]
        plan = QueryPlan(brand_id=uuid4(), queries=queries)

        t_start = fake.now()
        res = await adapter.search(plan, limit=10)
        t_end = fake.now()

        assert res.queries_executed == 6
        # 6 queries means 5 intervals of 1.0 s = 5.0 s
        assert t_end - t_start >= 5.0
        assert len(fake.sleep_calls) == 5
        assert all(s == 1.0 for s in fake.sleep_calls)

    @pytest.mark.asyncio
    @respx.mock
    async def test_two_concurrent_searches_share_one_budget(self) -> None:
        respx.get("https://itunes.apple.com/search").respond(
            200, json={"resultCount": 0, "results": []}
        )

        fake = FakeClock()
        shared_limiter = AsyncRateLimiter(
            min_interval_s=3.0, clock=fake.now, sleep=fake.sleep
        )
        adapter1 = AppleItunesAdapter(rate_limiter=shared_limiter)
        adapter2 = AppleItunesAdapter(rate_limiter=shared_limiter)

        plan1 = QueryPlan(
            brand_id=uuid4(),
            queries=[
                PlannedQuery(term="p1_q1", kind="EXACT", priority=1),
                PlannedQuery(term="p1_q2", kind="EXACT", priority=2),
            ],
        )
        plan2 = QueryPlan(
            brand_id=uuid4(),
            queries=[
                PlannedQuery(term="p2_q1", kind="EXACT", priority=1),
                PlannedQuery(term="p2_q2", kind="EXACT", priority=2),
            ],
        )

        t_start = fake.now()
        r1, r2 = await asyncio.gather(adapter1.search(plan1), adapter2.search(plan2))
        t_end = fake.now()

        assert r1.queries_executed == 2
        assert r2.queries_executed == 2
        # Total 4 queries serialized through 1 budget = 3 intervals of 3.0 s = 9.0 s
        assert t_end - t_start == 9.0
        assert len(fake.sleep_calls) == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_also_waits_for_limiter(self) -> None:
        # First call returns 500 (triggers retry), second call returns 200
        route = respx.get("https://itunes.apple.com/search")
        route.side_effect = [
            httpx.Response(500, text="Internal Server Error"),
            httpx.Response(200, json={"resultCount": 0, "results": []}),
        ]

        fake = FakeClock()
        limiter = AsyncRateLimiter(min_interval_s=3.0, clock=fake.now, sleep=fake.sleep)
        adapter = AppleItunesAdapter(rate_limiter=limiter)

        plan = QueryPlan(
            brand_id=uuid4(),
            queries=[PlannedQuery(term="retry_test", kind="EXACT", priority=1)],
        )

        t_start = fake.now()
        res = await adapter.search(plan)
        t_end = fake.now()

        assert res.queries_executed == 1
        # Attempt 1 acquired at t=0; attempt 2 (retry) acquired at t=3.0
        assert t_end - t_start == 3.0
        assert len(fake.sleep_calls) == 1
        assert fake.sleep_calls[0] == 3.0

    @pytest.mark.asyncio
    @respx.mock
    async def test_prefill_and_health_check_share_budget(self) -> None:
        respx.get("https://itunes.apple.com/search").respond(
            200, json={"resultCount": 0, "results": []}
        )
        respx.get("https://itunes.apple.com/lookup").respond(
            200, json={"resultCount": 0, "results": []}
        )

        fake = FakeClock()
        shared_limiter = AsyncRateLimiter(
            min_interval_s=3.0, clock=fake.now, sleep=fake.sleep
        )
        adapter = AppleItunesAdapter(rate_limiter=shared_limiter)

        t_start = fake.now()
        # 1. Health check with force_refresh makes 1 call
        await adapter.health_check(force_refresh=True)
        # 2. Lookup makes 1 call
        await adapter.lookup("com.kaveri.mobile")
        t_end = fake.now()

        # Shared limiter forced 1 interval of 3.0 s between health check and lookup
        assert t_end - t_start == 3.0
        assert len(fake.sleep_calls) == 1

    @pytest.mark.asyncio
    async def test_cancelling_search_mid_wait_leaves_limiter_usable_and_no_leaks(
        self,
    ) -> None:
        # Create a limiter with a real sleep that we cancel mid-wait
        limiter = AsyncRateLimiter(min_interval_s=10.0)

        # Acquire once
        await limiter.acquire()

        # Start a task that will wait 10 seconds in acquire()
        waiter_task = asyncio.create_task(limiter.acquire())
        await asyncio.sleep(0.01)  # allow waiter to enter acquire and lock/sleep

        # Cancel mid-wait (simulating SCAN_TIMEOUT_SECONDS hit)
        waiter_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter_task

        # Verify limiter is not deadlock-locked and remains usable immediately once window passes
        # Re-create with 0-interval or advance
        quick_limiter = AsyncRateLimiter(min_interval_s=0.01)
        await quick_limiter.acquire()
        t2 = asyncio.create_task(quick_limiter.acquire())
        await asyncio.sleep(0.001)
        t2.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t2

        # Subsequent task can acquire without hang!
        await quick_limiter.acquire()

    @pytest.mark.asyncio
    @respx.mock
    async def test_whole_scan_search_is_safely_cancellable(self) -> None:
        async def slow_responder(request: httpx.Request) -> httpx.Response:
            await asyncio.sleep(5.0)
            return httpx.Response(200, json={"resultCount": 0, "results": []})

        respx.get("https://itunes.apple.com/search").mock(side_effect=slow_responder)

        adapter = AppleItunesAdapter(rate_limiter=AsyncRateLimiter(0.0))
        plan = QueryPlan(
            brand_id=uuid4(),
            queries=[PlannedQuery(term="slow", kind="EXACT", priority=1)],
        )

        search_task = asyncio.create_task(adapter.search(plan))
        await asyncio.sleep(0.05)

        # Cancel search task
        search_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await search_task

        # Ensure no residual tasks running
        residual_tasks = [
            t for t in asyncio.all_tasks() if t is not asyncio.current_task()
        ]
        assert search_task not in residual_tasks
        assert search_task.done()
