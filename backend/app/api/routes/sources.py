"""Source status routes for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.1
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.core.prefill_service import _adapters
from app.schemas.enums import AssetType, SourceMode, SourceStatus
from app.schemas.source import SourceHealth

logger = logging.getLogger("threatlens.sources")

router = APIRouter(prefix="/sources", tags=["Sources"])


@router.get("/status", response_model=list[SourceHealth])
async def get_sources_status(
    refresh: bool = Query(default=False),
) -> list[SourceHealth]:
    """Retrieve external source coverage and connectivity status.

    Returns fixed list of 9 source IDs per Section 11.1.
    Google Play, Instagram, X and Facebook are explicitly NOT_CONNECTED.
    When refresh=True, performs a live health check for connected adapters.
    """
    now = datetime.now(timezone.utc)

    # 1. apple_itunes
    apple_health = SourceHealth(
        source_id="apple_itunes",
        display_name="Apple App Store search",
        platform="apple_app_store",
        asset_types=[AssetType.IOS_APP],
        status=SourceStatus.CONNECTED,
        supported_modes=[SourceMode.LIVE, SourceMode.CACHED],
        default_mode=SourceMode.LIVE,
        last_checked_at=now,
        rate_limit_note="About 20 requests per minute",
        message="Live catalog search available.",
    )
    if refresh and "apple_itunes" in _adapters:
        try:
            adapter_h = await _adapters["apple_itunes"].health_check()
            apple_health.status = adapter_h.status
            apple_health.last_checked_at = adapter_h.last_checked_at or now
            if adapter_h.message:
                apple_health.message = adapter_h.message
        except Exception as e:  # noqa: BLE001
            logger.warning("apple_itunes health check failed: %s", e)
            apple_health.status = SourceStatus.ERROR
            apple_health.message = f"Health check failed: {e}"

    # 2. bluesky_public
    bluesky_health = SourceHealth(
        source_id="bluesky_public",
        display_name="Bluesky Public Actor Search",
        platform="bluesky",
        asset_types=[AssetType.SOCIAL_ACCOUNT],
        status=SourceStatus.CONNECTED,
        supported_modes=[SourceMode.LIVE],
        default_mode=SourceMode.LIVE,
        last_checked_at=now,
        rate_limit_note=None,
        message="Live public actor search and profile enrichment available.",
    )
    if refresh and "bluesky_public" in _adapters:
        try:
            adapter_h = await _adapters["bluesky_public"].health_check()
            bluesky_health.status = adapter_h.status
            bluesky_health.last_checked_at = adapter_h.last_checked_at or now
            if adapter_h.message:
                bluesky_health.message = adapter_h.message
        except Exception as e:  # noqa: BLE001
            logger.warning("bluesky_public health check failed: %s", e)
            bluesky_health.status = SourceStatus.ERROR
            bluesky_health.message = f"Health check failed: {e}"

    # 3. bluesky_posts (P1 authenticated)
    bluesky_posts = SourceHealth(
        source_id="bluesky_posts",
        display_name="Bluesky Post Search",
        platform="bluesky",
        asset_types=[AssetType.SOCIAL_ACCOUNT],
        status=SourceStatus.NOT_CONNECTED,
        supported_modes=[SourceMode.LIVE],
        default_mode=None,
        last_checked_at=None,
        rate_limit_note=None,
        message="P1 authenticated search; not connected.",
    )

    # 4. google_play_snapshot (Explicitly NOT_CONNECTED)
    google_play = SourceHealth(
        source_id="google_play_snapshot",
        display_name="Google Play Store Snapshot",
        platform="google_play",
        asset_types=[AssetType.ANDROID_APP],
        status=SourceStatus.NOT_CONNECTED,
        supported_modes=[SourceMode.SIMULATED, SourceMode.CACHED],
        default_mode=None,
        last_checked_at=None,
        rate_limit_note=None,
        message="No official API; not queried",
    )

    # 5. instagram (Explicitly NOT_CONNECTED)
    instagram = SourceHealth(
        source_id="instagram",
        display_name="Instagram",
        platform="instagram",
        asset_types=[AssetType.SOCIAL_ACCOUNT],
        status=SourceStatus.NOT_CONNECTED,
        supported_modes=[SourceMode.SIMULATED],
        default_mode=None,
        last_checked_at=None,
        rate_limit_note=None,
        message="Requires platform API access",
    )

    # 6. x (Explicitly NOT_CONNECTED)
    x_source = SourceHealth(
        source_id="x",
        display_name="X (Twitter)",
        platform="x",
        asset_types=[AssetType.SOCIAL_ACCOUNT],
        status=SourceStatus.NOT_CONNECTED,
        supported_modes=[SourceMode.SIMULATED],
        default_mode=None,
        last_checked_at=None,
        rate_limit_note=None,
        message="Requires platform API access",
    )

    # 7. facebook (Explicitly NOT_CONNECTED)
    facebook = SourceHealth(
        source_id="facebook",
        display_name="Facebook",
        platform="facebook",
        asset_types=[AssetType.SOCIAL_ACCOUNT],
        status=SourceStatus.NOT_CONNECTED,
        supported_modes=[SourceMode.SIMULATED],
        default_mode=None,
        last_checked_at=None,
        rate_limit_note=None,
        message="Requires platform API access",
    )

    # 8. demo_fixtures
    demo_fixtures = SourceHealth(
        source_id="demo_fixtures",
        display_name="Demo Fixtures",
        platform="fixtures",
        asset_types=[AssetType.IOS_APP, AssetType.SOCIAL_ACCOUNT, AssetType.ANDROID_APP],
        status=SourceStatus.CONNECTED,
        supported_modes=[SourceMode.SIMULATED, SourceMode.CACHED],
        default_mode=SourceMode.SIMULATED,
        last_checked_at=now,
        rate_limit_note=None,
        message="Available only in DEMO scans.",
    )

    # 9. recorded_fixtures
    recorded_fixtures = SourceHealth(
        source_id="recorded_fixtures",
        display_name="Recorded Fixtures",
        platform="fixtures",
        asset_types=[AssetType.IOS_APP, AssetType.SOCIAL_ACCOUNT],
        status=SourceStatus.CONNECTED,
        supported_modes=[SourceMode.CACHED],
        default_mode=SourceMode.CACHED,
        last_checked_at=now,
        rate_limit_note=None,
        message="Available only in DEMO scans.",
    )

    return [
        apple_health,
        bluesky_health,
        bluesky_posts,
        google_play,
        instagram,
        x_source,
        facebook,
        demo_fixtures,
        recorded_fixtures,
    ]
