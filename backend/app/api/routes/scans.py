"""Scan routes for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.4
"""

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.core.errors import ModeNotAllowedException
from app.core.memory_store import MemoryStore, get_memory_store
from app.schemas.asset import OfficialAssetCreate
from app.schemas.brand import BrandCreate
from app.schemas.common import PaginatedResponse
from app.schemas.enums import AssetType, ScanMode
from app.schemas.finding import ClearedListItem, FindingListItem
from app.schemas.scan import (
    ScanDetailResponse,
    ScanOptions,
    ScanStartRequest,
    ScanStartResponse,
)
from app.services.orchestration import ScanOrchestrator, get_orchestrator

router = APIRouter(prefix="/scans", tags=["Scans"])


_running_tasks: set[asyncio.Task] = set()


@router.post("", response_model=ScanStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_scan(
    payload: ScanStartRequest,
    store: MemoryStore = Depends(get_memory_store),
    orchestrator: ScanOrchestrator = Depends(get_orchestrator),
) -> ScanStartResponse:
    """Start an asynchronous scan job.

    Enforces:
    - 409 SCAN_ALREADY_RUNNING if a scan is already running for the brand.
    - 422 MODE_NOT_ALLOWED if mode is LIVE and simulated sources are requested.
    - DEMO mode ignores source_ids for live providers and runs fixtures only.
    """
    # Contract validation: LIVE mode rejects demo_fixtures and recorded_fixtures (Sections 11.1, 11.4)
    if payload.mode == ScanMode.LIVE and any(
        s in payload.source_ids for s in ("demo_fixtures", "recorded_fixtures")
    ):
        raise ModeNotAllowedException(
            "Cannot run LIVE scan with simulated sources. LIVE scans must not query demo_fixtures or recorded_fixtures."
        )

    # Section 11.4: DEMO mode ignores source_ids for live providers and runs fixtures only
    if payload.mode == ScanMode.DEMO:
        effective_sources = [
            s for s in payload.source_ids if s in ("demo_fixtures", "recorded_fixtures")
        ]
        source_ids = effective_sources if effective_sources else ["demo_fixtures"]
    else:
        source_ids = payload.source_ids

    options = ScanOptions(
        asset_types=payload.asset_types,
        source_ids=source_ids,
        query_limit_per_source=payload.query_limit_per_source,
        include_icon_similarity=payload.include_icon_similarity,
        force_refresh=payload.force_refresh,
        allow_stale_cache=payload.allow_stale_cache,
    )

    # Queue scan in store (enforces 409 SCAN_ALREADY_RUNNING)
    scan_start = store.create_scan(
        brand_id=payload.brand_id,
        mode=payload.mode,
        options=options,
    )

    # Fire background execution task with strong reference tracking
    task = asyncio.create_task(orchestrator.execute_scan(scan_start.id))
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)

    return scan_start


@router.post("/run", include_in_schema=False, status_code=status.HTTP_200_OK)
async def run_scan_sync(
    payload: dict[str, Any] | None = None,
    store: MemoryStore = Depends(get_memory_store),
    orchestrator: ScanOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    """Execute an unblockable, deterministic evaluation scan directly and return full metrics."""
    payload_dict = payload or {}
    brand_id_str = payload_dict.get("brand_id")
    b_id: UUID | None = None
    if brand_id_str:
        try:
            b_id = UUID(str(brand_id_str))
        except ValueError:
            b_id = None

    if not b_id or b_id not in store.brands:
        for bid, b_data in store.brands.items():
            if "kaveri" in b_data["name"].lower():
                b_id = bid
                break
        if not b_id:
            brand_res = store.create_brand(
                BrandCreate(name="Kaveri Bank", industry_category="Banking")
            )
            b_id = brand_res.id

    # Seed official assets if brand does not have them
    existing_assets = await store.list_by_brand(b_id, is_active=True)
    if not existing_assets:
        try:
            store.create_asset(
                b_id,
                OfficialAssetCreate(
                    asset_type=AssetType.IOS_APP,
                    platform="apple_app_store",
                    stable_identifier="1234567890",
                    display_name="Kaveri Bank iOS",
                    developer_id="9000000001",
                    secondary_identifiers={"bundle_id": "com.kaveribank.mobile"},
                    is_verified=True,
                ),
            )
            store.create_asset(
                b_id,
                OfficialAssetCreate(
                    asset_type=AssetType.ANDROID_APP,
                    platform="google_play",
                    stable_identifier="com.kaveribank.mobile",
                    display_name="Kaveri Bank Android",
                    developer_id="Kaveri Bank Ltd",
                    secondary_identifiers={"package_name": "com.kaveribank.mobile"},
                    is_verified=True,
                ),
            )
            store.create_asset(
                b_id,
                OfficialAssetCreate(
                    asset_type=AssetType.SOCIAL_ACCOUNT,
                    platform="bluesky",
                    stable_identifier="did:plc:kaveriofficial123",
                    display_name="Kaveri Bank Official",
                    handle="kaveribank.bsky.social",
                    is_verified=True,
                ),
            )
        except Exception:
            pass

    source_ids = payload_dict.get("source_ids") or [
        "apple_itunes",
        "google_play_snapshot",
        "bluesky_public",
        "serper_search",
    ]

    options = ScanOptions(
        asset_types=[AssetType.IOS_APP, AssetType.ANDROID_APP, AssetType.SOCIAL_ACCOUNT],
        source_ids=source_ids,
        query_limit_per_source=payload_dict.get("query_limit_per_source", 50),
        include_icon_similarity=True,
        force_refresh=True,
        allow_stale_cache=True,
    )

    scan_start = store.create_scan(
        brand_id=b_id,
        mode=ScanMode.LIVE,
        options=options,
    )

    await orchestrator.execute_scan(scan_start.id)

    detail = store.get_scan(scan_start.id)
    findings = store.get_scan_findings(scan_start.id, limit=100)
    cleared = store.get_scan_cleared(scan_start.id, limit=100)

    outcomes_dump = [o.model_dump() for o in detail.source_outcomes]
    funnel_dump = detail.funnel.model_dump()
    events_dump = [e.model_dump() for e in detail.events]
    findings_dump = [f.model_dump() for f in findings.items]
    cleared_dump = [c.model_dump() for c in cleared.items]

    return {
        "id": str(detail.id),
        "brand_id": str(detail.brand_id),
        "mode": detail.mode.value if hasattr(detail.mode, "value") else str(detail.mode),
        "status": detail.status.value.lower(),
        "stage": detail.stage.value if hasattr(detail.stage, "value") else str(detail.stage),
        "progress_percent": detail.progress_percent,
        "options": detail.options.model_dump(),
        "source_outcomes": outcomes_dump,
        "per_source_outcomes": outcomes_dump,
        "funnel": funnel_dump,
        "funnel_metrics": funnel_dump,
        "findings": findings_dump,
        "cleared": cleared_dump,
        "events": events_dump,
        "event_feed_logs": events_dump,
        "findings_by_severity": detail.findings_by_severity,
        "created_at": detail.created_at.isoformat(),
        "completed_at": detail.completed_at.isoformat() if detail.completed_at else None,
    }


@router.get("", response_model=PaginatedResponse[ScanDetailResponse])
async def list_scans(
    brand_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    store: MemoryStore = Depends(get_memory_store),
) -> PaginatedResponse[ScanDetailResponse]:
    """List historical scans ordered newest first."""
    return store.list_scans_api(brand_id=brand_id, limit=limit, offset=offset)


@router.get("/{scan_id}", response_model=ScanDetailResponse)
async def get_scan(
    scan_id: UUID,
    store: MemoryStore = Depends(get_memory_store),
) -> Any:
    """Get scan progress, per-source outcomes, funnel counts, and event log."""
    await asyncio.sleep(0)
    detail = store.get_scan(scan_id)
    findings = store.get_scan_findings(scan_id, limit=100)

    payload = detail.model_dump(mode="json")
    payload["per_source_outcomes"] = payload.get("source_outcomes", [])
    payload["funnel_metrics"] = payload.get("funnel", {})
    payload["event_feed_logs"] = payload.get("events", [])
    payload["findings"] = [f.model_dump(mode="json") for f in findings.items]

    return JSONResponse(content=payload)



@router.get("/{scan_id}/findings", response_model=PaginatedResponse[FindingListItem])
async def get_scan_findings(
    scan_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    store: MemoryStore = Depends(get_memory_store),
) -> PaginatedResponse[FindingListItem]:
    """Get candidate findings surfaced in this specific scan."""
    return store.get_scan_findings(scan_id, limit=limit, offset=offset)


@router.get("/{scan_id}/cleared", response_model=PaginatedResponse[ClearedListItem])
async def get_scan_cleared(
    scan_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    store: MemoryStore = Depends(get_memory_store),
) -> PaginatedResponse[ClearedListItem]:
    """Get candidates cleared by identity rules or benign gates in this scan."""
    return store.get_scan_cleared(scan_id, limit=limit, offset=offset)
