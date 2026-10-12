"""Brand routes for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.2
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.memory_store import MemoryStore, get_memory_store
from app.schemas.brand import (
    AuditEventResponse,
    BrandCreate,
    BrandResponse,
    BrandSummaryResponse,
    BrandUpdate,
)
from app.schemas.common import PaginatedResponse
from app.schemas.enums import IdentityDecision
from app.schemas.finding import ClearedListItem

router = APIRouter(prefix="/brands", tags=["Brands"])


@router.post("", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
    payload: BrandCreate,
    store: MemoryStore = Depends(get_memory_store),
) -> BrandResponse:
    """Register a new brand profile."""
    return store.create_brand(payload)


@router.get("", response_model=PaginatedResponse[BrandResponse])
async def list_brands(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    store: MemoryStore = Depends(get_memory_store),
) -> PaginatedResponse[BrandResponse]:
    """List registered brands with pagination."""
    return store.list_brands_api(limit=limit, offset=offset)


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: UUID,
    store: MemoryStore = Depends(get_memory_store),
) -> BrandResponse:
    """Get brand profile details and asset count."""
    return store.get_brand(brand_id)


@router.patch("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: UUID,
    payload: BrandUpdate,
    store: MemoryStore = Depends(get_memory_store),
) -> BrandResponse:
    """Update permitted fields of a brand profile."""
    return store.update_brand(brand_id, payload)


@router.get("/{brand_id}/summary", response_model=BrandSummaryResponse)
async def get_brand_summary(
    brand_id: UUID,
    store: MemoryStore = Depends(get_memory_store),
) -> BrandSummaryResponse:
    """Get brand monitoring overview aggregates, funnel metrics, and coverage."""
    return store.get_brand_summary(brand_id)


@router.get(
    "/{brand_id}/cleared",
    response_model=PaginatedResponse[ClearedListItem],
)
async def list_brand_cleared(
    brand_id: UUID,
    decision: IdentityDecision | None = Query(default=None),
    scan_id: UUID | None = Query(default=None),
    platform: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    store: MemoryStore = Depends(get_memory_store),
) -> PaginatedResponse[ClearedListItem]:
    """List cleared items for a brand with optional filtering and pagination."""
    return store.list_brand_cleared(
        brand_id=brand_id,
        decision=decision,
        scan_id=scan_id,
        platform=platform,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{brand_id}/audit",
    response_model=PaginatedResponse[AuditEventResponse],
)
async def list_brand_audit(
    brand_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    store: MemoryStore = Depends(get_memory_store),
) -> PaginatedResponse[AuditEventResponse]:
    """List audit events for a brand ordered newest first."""
    return store.list_brand_audit(brand_id=brand_id, limit=limit, offset=offset)
