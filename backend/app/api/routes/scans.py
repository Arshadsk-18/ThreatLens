"""Scan routes for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.4
"""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.errors import ModeNotAllowedException
from app.core.memory_store import MemoryStore, get_memory_store
from app.schemas.common import PaginatedResponse
from app.schemas.enums import ScanMode
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
) -> ScanDetailResponse:
    """Get scan progress, per-source outcomes, funnel counts, and event log."""
    await asyncio.sleep(0)
    return store.get_scan(scan_id)



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
