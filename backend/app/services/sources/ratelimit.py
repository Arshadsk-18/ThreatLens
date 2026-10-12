"""Async rate limiting for external source providers.

Owner: Person 3 (backend/app/services/sources/ratelimit.py)
Reference: Contract Sections 5.5, 12
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from typing import Any, Self


class AsyncRateLimiter:
    """Async rate limiter enforcing a minimum interval between the START of consecutive calls.

    Designed to be used as `async with limiter:`.
    Guarantees:
    - At least `min_interval_s` between the START of consecutive executions.
    - Concurrency-safe across asyncio tasks using an internal asyncio.Lock.
    - Cancellation-safe: if a waiting task is cancelled while sleeping, the next
      allowed start timestamp is preserved so subsequent waiters are not starved or delayed.
    - Clock and sleep are injectable for zero-delay deterministic testing.
    """

    def __init__(
        self,
        min_interval_s: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Coroutine[Any, Any, None]] = asyncio.sleep,
    ) -> None:
        self.min_interval_s = max(0.0, float(min_interval_s))
        self._clock = clock
        self._sleep = sleep
        self._next_allowed_start = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until the next allowed start window and record the new window."""
        if self.min_interval_s <= 0.0:
            return

        async with self._lock:
            now = self._clock()
            wait_time = self._next_allowed_start - now
            if wait_time > 0.0:
                await self._sleep(wait_time)
            # Only reached if the sleep was not cancelled
            actual_start = self._clock()
            self._next_allowed_start = actual_start + self.min_interval_s

    async def __aenter__(self) -> Self:
        await self.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        pass


# Module-level shared limiters so scans, prefill lookups, and health checks share the budget
APPLE_LIMITER = AsyncRateLimiter(3.0)
BLUESKY_LIMITER = AsyncRateLimiter(1.0)
