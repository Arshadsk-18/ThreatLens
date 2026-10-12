"""Official asset routes for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.3
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.memory_store import MemoryStore, get_memory_store
from app.core.prefill_parser import parse_and_validate_prefill
from app.core.prefill_service import perform_prefill_lookup
from app.schemas.asset import (
    AssetPrefillRequest,
    AssetPrefillResponse,
    OfficialAssetCreate,
    OfficialAssetResponse,
    OfficialAssetUpdate,
)
from app.schemas.common import PaginatedResponse
from app.schemas.enums import AssetType, Relationship

router = APIRouter(prefix="/brands/{brand_id}/assets", tags=["Official Assets"])


@router.post("/prefill", response_model=AssetPrefillResponse)
async def prefill_asset(
    brand_id: UUID,
    payload: AssetPrefillRequest,
    store: MemoryStore = Depends(get_memory_store),
) -> AssetPrefillResponse:
    """Generate draft asset metadata from store link or platform identifier.

    Does NOT persist any asset. Never fetches arbitrary user URLs.
    Unallowlisted URLs return 422 VALIDATION_ERROR with BLOCKED_URL details.
    """
    # Ensure brand exists
    store.get_brand(brand_id)

    # Allowlist and parse URL / identifier
    target = parse_and_validate_prefill(
        url=payload.url,
        platform=payload.platform,
        identifier=payload.identifier,
    )

    # Perform lookup via provider adapter or test double
    return await perform_prefill_lookup(target)


@router.post(
    "", response_model=OfficialAssetResponse, status_code=status.HTTP_201_CREATED
)
async def register_asset(
    brand_id: UUID,
    payload: OfficialAssetCreate,
    store: MemoryStore = Depends(get_memory_store),
) -> OfficialAssetResponse:
    """Register an official or authorized partner asset."""
    return store.create_asset(brand_id, payload)


@router.get("", response_model=PaginatedResponse[OfficialAssetResponse])
async def list_assets(
    brand_id: UUID,
    asset_type: AssetType | None = Query(default=None),
    relationship: Relationship | None = Query(default=None),
    is_verified: bool | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    store: MemoryStore = Depends(get_memory_store),
) -> PaginatedResponse[OfficialAssetResponse]:
    """List official assets for a brand with filtering and pagination."""
    return store.list_assets_api(
        brand_id=brand_id,
        asset_type=asset_type,
        relationship=relationship,
        is_verified=is_verified,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )


@router.get("/{asset_id}", response_model=OfficialAssetResponse)
async def get_asset(
    brand_id: UUID,
    asset_id: UUID,
    store: MemoryStore = Depends(get_memory_store),
) -> OfficialAssetResponse:
    """Get registered asset details by asset ID."""
    return store.get_asset(brand_id, asset_id)


@router.patch("/{asset_id}", response_model=OfficialAssetResponse)
async def update_asset(
    brand_id: UUID,
    asset_id: UUID,
    payload: OfficialAssetUpdate,
    store: MemoryStore = Depends(get_memory_store),
) -> OfficialAssetResponse:
    """Update or deactivate an asset. Writes an audit event."""
    return store.update_asset(brand_id, asset_id, payload)
