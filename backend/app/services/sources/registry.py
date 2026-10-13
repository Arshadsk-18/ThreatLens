"""Central Source Adapter Registry and Status Catalog.

Owner: Person 3 (backend/app/services/sources/registry.py)
Reference: Contract Sections 5.3, 11.1, 12

Manages the nine fixed source adapters:
1. apple_itunes (LIVE, CACHED)
2. bluesky_public (LIVE, CACHED)
3. bluesky_posts (NOT_CONNECTED)
4. google_play_snapshot (NOT_CONNECTED)
5. instagram (NOT_CONNECTED)
6. x (NOT_CONNECTED)
7. facebook (NOT_CONNECTED)
8. demo_fixtures (SIMULATED, DEMO-only)
9. recorded_fixtures (CACHED, DEMO-only)
"""

from __future__ import annotations

from typing import Any

from app.schemas import AssetType, SourceHealth, SourceMode

from .apple import AppleItunesAdapter
from .base import SourceAdapter
from .bluesky import BlueskyPublicAdapter
from .google_play import GooglePlaySnapshotAdapter
from .serper import SerperSearchAdapter
from .fixtures_demo import DemoFixtureAdapter
from .fixtures_recorded import RecordedFixtureAdapter
from .not_connected import NotConnectedAdapter

DEMO_ONLY_SOURCES = frozenset({"demo_fixtures", "recorded_fixtures"})

# Exact fixed order of 9 source IDs per Contract Section 11.1
FIXED_SOURCE_IDS = (
    "apple_itunes",
    "bluesky_public",
    "bluesky_posts",
    "google_play_snapshot",
    "instagram",
    "x",
    "facebook",
    "demo_fixtures",
    "recorded_fixtures",
)


class AwaitableList(list):
    """List that can be returned synchronously or awaited asynchronously."""

    def __await__(self) -> Any:
        async def _wrap() -> list:
            return self

        return _wrap().__await__()


class SourceRegistry:
    """Singleton registry maintaining live adapter state across requests."""

    def __init__(self) -> None:
        self._adapters: dict[str, SourceAdapter] = {}
        self._init_adapters()

    def _init_adapters(self) -> None:
        # 1. Live connectors
        self._adapters["apple_itunes"] = AppleItunesAdapter()
        self._adapters["bluesky_public"] = BlueskyPublicAdapter()
        self._adapters["google_play_snapshot"] = GooglePlaySnapshotAdapter()
        self._adapters["serper_search"] = SerperSearchAdapter()

        # 2. Not connected connectors
        self._adapters["bluesky_posts"] = NotConnectedAdapter(
            source_id="bluesky_posts",
            display_name="Bluesky post search",
            message="Post search not enabled in P0; not queried.",
            platform="bluesky",
            asset_types=[AssetType.SOCIAL_ACCOUNT],
        )
        self._adapters["instagram"] = NotConnectedAdapter(
            source_id="instagram",
            display_name="Instagram profile search",
            message="Requires platform API access. Not queried.",
            platform="instagram",
            asset_types=[AssetType.SOCIAL_ACCOUNT],
        )
        self._adapters["x"] = NotConnectedAdapter(
            source_id="x",
            display_name="X (Twitter) search",
            message="Requires platform API access. Not queried.",
            platform="x",
            asset_types=[AssetType.SOCIAL_ACCOUNT],
        )
        self._adapters["facebook"] = NotConnectedAdapter(
            source_id="facebook",
            display_name="Facebook Page search",
            message="Requires platform API access. Not queried.",
            platform="facebook",
            asset_types=[AssetType.SOCIAL_ACCOUNT],
        )

        # 3. Fixture connectors (DEMO only)
        self._adapters["demo_fixtures"] = DemoFixtureAdapter()
        self._adapters["recorded_fixtures"] = RecordedFixtureAdapter()

    def get_adapter(self, source_id: str, is_live_scan: bool = False) -> SourceAdapter:
        if source_id not in self._adapters:
            raise KeyError(f"Unknown source adapter '{source_id}'")

        if is_live_scan and is_demo_only(source_id):
            raise ValueError(
                f"Source '{source_id}' is demo-only and cannot be used in a LIVE scan (MODE_NOT_ALLOWED)."
            )

        return self._adapters[source_id]

    def list_adapters(self) -> list[SourceAdapter]:
        return [
            self._adapters[sid] for sid in FIXED_SOURCE_IDS if sid in self._adapters
        ]

    def source_catalog(self) -> AwaitableList:
        """Return catalog of all 9 source health entries (synchronously or awaitable)."""
        entries = []
        for sid in FIXED_SOURCE_IDS:
            adapter = self._adapters.get(sid)
            if not adapter:
                continue
            # Extract health without network (reflecting last real outcome)
            if hasattr(adapter, "_last_health_status"):
                # Live adapter: Apple, Bluesky, or Google Play
                platform = (
                    "apple_app_store"
                    if "apple" in sid
                    else ("google_play" if "google" in sid else "bluesky")
                )
                asset_types = (
                    [AssetType.IOS_APP]
                    if "apple" in sid
                    else (
                        [AssetType.ANDROID_APP]
                        if "google" in sid
                        else [AssetType.SOCIAL_ACCOUNT]
                    )
                )
                rate_limit_note = (
                    "Snapshot query quota: ~60 req/min"
                    if "google" in sid
                    else (
                        "Rate limited"
                        if "apple" in sid
                        else "Conservative rate limit"
                    )
                )
                health = SourceHealth(
                    source_id=adapter.source_id,
                    display_name=getattr(adapter, "display_name", adapter.source_id),
                    platform=platform,
                    asset_types=asset_types,
                    status=adapter._last_health_status,
                    supported_modes=[SourceMode.LIVE, SourceMode.CACHED],
                    default_mode=SourceMode.LIVE,
                    last_checked_at=adapter._last_checked_at,
                    rate_limit_note=rate_limit_note,
                    message=adapter._last_health_message,
                )
            elif isinstance(adapter, NotConnectedAdapter):
                from app.schemas import SourceStatus

                health = SourceHealth(
                    source_id=adapter.source_id,
                    display_name=adapter.display_name,
                    platform=adapter.platform,
                    asset_types=adapter.asset_types,
                    status=SourceStatus.NOT_CONNECTED,
                    supported_modes=[],
                    default_mode=SourceMode.LIVE,
                    last_checked_at=None,
                    rate_limit_note="Not connected",
                    message=adapter.message,
                )

            elif isinstance(adapter, DemoFixtureAdapter):
                from app.schemas import SourceStatus

                health = SourceHealth(
                    source_id="demo_fixtures",
                    display_name="Demo Fixtures (Simulated)",
                    platform="demo",
                    asset_types=[
                        AssetType.IOS_APP,
                        AssetType.ANDROID_APP,
                        AssetType.SOCIAL_ACCOUNT,
                    ],
                    status=SourceStatus.CONNECTED,
                    supported_modes=[SourceMode.SIMULATED],
                    default_mode=SourceMode.SIMULATED,
                    last_checked_at=None,
                    rate_limit_note="No rate limit (local fixtures)",
                    message="Offline simulated fixtures available for DEMO scans.",
                )
            elif isinstance(adapter, RecordedFixtureAdapter):
                from app.schemas import SourceStatus

                health = SourceHealth(
                    source_id="recorded_fixtures",
                    display_name="Recorded Real Fixtures",
                    platform="multi",
                    asset_types=[AssetType.IOS_APP, AssetType.SOCIAL_ACCOUNT],
                    status=SourceStatus.CONNECTED,
                    supported_modes=[SourceMode.CACHED],
                    default_mode=SourceMode.CACHED,
                    last_checked_at=None,
                    rate_limit_note="No rate limit (local recorded files)",
                    message="Recorded real provider responses served offline as CACHED.",
                )
            else:
                continue
            entries.append(health)
        return AwaitableList(entries)

    async def refresh_status(self, source_id: str) -> SourceHealth:
        """Trigger one live health check for live adapters only (refresh=true support)."""
        adapter = self.get_adapter(source_id)
        if hasattr(adapter, "health_check"):
            return await adapter.health_check(force_refresh=True)
        return await adapter.health_check()


# Module-level registry singleton
_REGISTRY = SourceRegistry()


def is_demo_only(source_id: str) -> bool:
    """Return True if source_id is a demo-only adapter."""
    return source_id in DEMO_ONLY_SOURCES


def assert_not_demo_only(source_id: str) -> None:
    """Raise ValueError if source_id is demo-only in a live context."""
    if is_demo_only(source_id):
        raise ValueError(
            f"Source '{source_id}' is demo-only and cannot be used in a LIVE scan (MODE_NOT_ALLOWED)."
        )


def get_adapter(source_id: str, is_live_scan: bool = False) -> SourceAdapter:
    """Retrieve adapter by source_id, raising if requested by a LIVE scan for demo sources."""
    return _REGISTRY.get_adapter(source_id, is_live_scan=is_live_scan)


def list_adapters() -> list[SourceAdapter]:
    """List all nine registered source adapters."""
    return _REGISTRY.list_adapters()


def source_catalog() -> AwaitableList:
    """Return the health catalog for all nine sources (sync or awaitable)."""
    return _REGISTRY.source_catalog()


async def refresh_status(source_id: str) -> SourceHealth:
    """Perform a live status refresh probe for the specified source."""
    return await _REGISTRY.refresh_status(source_id)


__all__ = [
    "DEMO_ONLY_SOURCES",
    "FIXED_SOURCE_IDS",
    "SourceRegistry",
    "assert_not_demo_only",
    "get_adapter",
    "is_demo_only",
    "list_adapters",
    "refresh_status",
    "source_catalog",
]
