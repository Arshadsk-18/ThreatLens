"""NotConnected source adapter stub for unconfigured or unsupported external platforms.

Owner: Person 3 (backend/app/services/sources/not_connected.py)
Reference: Contract Sections 5.5, 11.1, 12

Status Rule:
Returns SourceStatus.NOT_CONNECTED with error_code=None (NOT an error).
search() returns empty candidates, queries_executed=0, cache_hit_count=0, duration_ms=0.
lookup() returns None.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.schemas import (
    AssetType,
    NormalizedCandidate,
    QueryPlan,
    SourceHealth,
    SourceMode,
    SourceResult,
    SourceStatus,
)


class NotConnectedAdapter:
    """Adapter for sources that are not connected in the current environment."""

    def __init__(
        self,
        source_id: str,
        display_name: str,
        message: str,
        platform: str = "generic",
        asset_types: list[AssetType] | None = None,
    ) -> None:
        self.source_id = source_id
        self.display_name = display_name
        self.message = message
        self.platform = platform
        self.asset_types = asset_types or [AssetType.SOCIAL_ACCOUNT]

    async def health_check(self) -> SourceHealth:
        """Report NOT_CONNECTED status with explaining message."""
        return SourceHealth(
            source_id=self.source_id,
            display_name=self.display_name,
            platform=self.platform,
            asset_types=self.asset_types,
            status=SourceStatus.NOT_CONNECTED,
            supported_modes=[],
            default_mode=SourceMode.LIVE,
            last_checked_at=datetime.now(UTC),
            rate_limit_note="Not connected",
            message=self.message,
        )

    async def search(
        self,
        plan: QueryPlan,
        limit: int = 50,
        *,
        force_refresh: bool = False,
        allow_stale_cache: bool = False,
    ) -> SourceResult:
        """Return NOT_CONNECTED status with 0 executed queries and NO error code."""
        return SourceResult(
            source_id=self.source_id,
            status=SourceStatus.NOT_CONNECTED,
            source_mode=None,
            retrieved_at=datetime.now(UTC),
            candidates=[],
            queries_executed=0,
            cache_hit_count=0,
            error_code=None,
            message=self.message,
            duration_ms=0,
        )

    async def lookup(self, identifier: str) -> NormalizedCandidate | None:
        """Not connected adapters cannot look up external assets."""
        return None


__all__ = ["NotConnectedAdapter"]
