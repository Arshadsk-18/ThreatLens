"""Hardening property tests: 500 seeded random fuzz iterations (Section G).

Owner: Person 3
Reference: Contract Sections 5.5, 12, Phase 9 Hardening
"""

from __future__ import annotations

import random
from typing import Any
from uuid import uuid4

import pytest
import respx
from app.schemas import PlannedQuery, QueryPlan, SourceResult
from app.services.sources.apple import AppleItunesAdapter
from app.services.sources.bluesky import BlueskyPublicAdapter
from app.services.sources.errors import ProviderError
from app.services.sources.ratelimit import AsyncRateLimiter


def generate_random_json_garbage(rng: random.Random, depth: int = 0) -> Any:
    """Generate arbitrary JSON-shaped garbage of arbitrary types and nesting."""
    if depth > 4:
        return rng.choice(
            [None, True, False, 0, 12345, -99.9, "", "garbage", "🚀\u0000\u200b"]
        )

    choice = rng.randint(0, 7)
    if choice == 0:
        return None
    if choice == 1:
        return rng.choice([True, False])
    if choice == 2:
        return rng.choice([0, -1, 42, 99999999, 3.14159, -0.001])
    if choice == 3:
        return rng.choice(
            [
                "",
                "normal string",
                "emoji 📱💰",
                "rtl بنك",
                "nul\x00byte",
                "control\x07\x1b",
                "very_long_" * 50,
                "handle.invalid",
                "https://user:pass@evil.com",
                "javascript:void(0)",
            ]
        )
    if choice == 4:
        # List of items
        size = rng.randint(0, 5)
        return [generate_random_json_garbage(rng, depth + 1) for _ in range(size)]
    if choice == 5:
        # Dict with random keys
        keys = [
            "trackId",
            "trackName",
            "bundleId",
            "sellerName",
            "actors",
            "did",
            "handle",
            "results",
            "foo",
            "bar",
        ]
        sub_keys = rng.sample(keys, k=rng.randint(0, len(keys)))
        return {k: generate_random_json_garbage(rng, depth + 1) for k in sub_keys}
    if choice == 6:
        # Typical Apple-like or Bluesky-like wrapper with corrupted insides
        return {
            "resultCount": rng.choice([None, 0, "5", -1, [1, 2]]),
            "results": [
                generate_random_json_garbage(rng, depth + 1)
                for _ in range(rng.randint(0, 3))
            ],
        }
    # Bluesky-like wrapper
    return {
        "actors": [
            generate_random_json_garbage(rng, depth + 1)
            for _ in range(rng.randint(0, 3))
        ],
        "profiles": [
            generate_random_json_garbage(rng, depth + 1)
            for _ in range(rng.randint(0, 3))
        ],
    }


class TestFuzzPropertyHardening:
    """Property fuzz testing with 500 seeded iterations."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_apple_adapter_fuzz_property_500_iterations(self) -> None:
        rng = random.Random(20261012)
        route = respx.get("https://itunes.apple.com/search")

        adapter = AppleItunesAdapter(rate_limiter=AsyncRateLimiter(0.0))
        plan = QueryPlan(
            brand_id=uuid4(),
            queries=[PlannedQuery(term="fuzz", kind="EXACT", priority=1)],
        )

        for i in range(500):
            garbage = generate_random_json_garbage(rng)
            route.respond(200, json=garbage)

            try:
                res = await adapter.search(plan)
                # If it didn't raise, it MUST be a valid SourceResult
                assert isinstance(res, SourceResult)
                assert res.source_id == "apple_itunes"
            except ProviderError:
                # Expected when response structure is completely invalid
                pass
            except Exception as err:  # noqa: BLE001
                pytest.fail(
                    f"Apple adapter raised unhandled exception on fuzz iteration {i}: {type(err).__name__}: {err}"
                )

    @pytest.mark.asyncio
    @respx.mock
    async def test_bluesky_adapter_fuzz_property_500_iterations(self) -> None:
        rng = random.Random(20261012)
        route_search = respx.get(
            "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
        )
        route_enrich = respx.get(
            "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles"
        )

        adapter = BlueskyPublicAdapter(rate_limiter=AsyncRateLimiter(0.0))
        plan = QueryPlan(
            brand_id=uuid4(),
            queries=[PlannedQuery(term="fuzz", kind="EXACT", priority=1)],
        )

        for i in range(500):
            garbage_search = generate_random_json_garbage(rng)
            garbage_enrich = generate_random_json_garbage(rng)

            route_search.respond(200, json=garbage_search)
            route_enrich.respond(200, json=garbage_enrich)

            try:
                res = await adapter.search(plan)
                assert isinstance(res, SourceResult)
                assert res.source_id == "bluesky_public"
            except ProviderError:
                pass
            except Exception as err:  # noqa: BLE001
                pytest.fail(
                    f"Bluesky adapter raised unhandled exception on fuzz iteration {i}: {type(err).__name__}: {err}"
                )
