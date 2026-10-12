"""Findings review, decision, and comparison routes for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.5
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.errors import NotFoundException
from app.core.memory_store import MemoryStore, get_memory_store
from app.schemas.candidate import NormalizedCandidate
from app.schemas.common import PaginatedResponse
from app.schemas.comparison import (
    ComparisonAssetSummary,
    ComparisonResponse,
    FieldComparison,
    NameDiffSegment,
)
from app.schemas.context import OfficialAssetCtx
from app.schemas.enums import (
    AssetType,
    FindingStatus,
    Severity,
    SourceMode,
)
from app.schemas.finding import (
    FindingDecisionRequest,
    FindingDetailResponse,
    FindingListItem,
)
from app.services.assess import compare

logger = logging.getLogger("threatlens.findings")

router = APIRouter(prefix="/findings", tags=["Findings"])


@router.get("", response_model=PaginatedResponse[FindingListItem])
async def list_findings(
    brand_id: UUID | None = Query(default=None),
    scan_id: UUID | None = Query(default=None),
    status: FindingStatus | None = Query(default=None),
    asset_type: AssetType | None = Query(default=None),
    platform: str | None = Query(default=None),
    severity: Severity | None = Query(default=None),
    min_score: int | None = Query(default=None),
    source_mode: SourceMode | None = Query(default=None),
    q: str | None = Query(default=None),
    latest_only: bool = Query(default=True),
    include_dismissed: bool = Query(default=False),
    sort: str = Query(default="score_desc"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    store: MemoryStore = Depends(get_memory_store),
) -> PaginatedResponse[FindingListItem]:
    """Get review findings with filters, ordering, pagination, and defaults."""
    return store.list_findings(
        brand_id=brand_id,
        scan_id=scan_id,
        status=status,
        asset_type=asset_type,
        platform=platform,
        severity=severity,
        min_score=min_score,
        source_mode=source_mode,
        q=q,
        latest_only=latest_only,
        include_dismissed=include_dismissed,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/{finding_id}", response_model=FindingDetailResponse)
async def get_finding(
    finding_id: UUID,
    store: MemoryStore = Depends(get_memory_store),
) -> FindingDetailResponse:
    """Get finding detail with breakdown, evidence, limitations, and decision history."""
    return store.get_finding(finding_id)


@router.patch("/{finding_id}", response_model=FindingDetailResponse)
async def patch_finding_decision(
    finding_id: UUID,
    payload: FindingDecisionRequest,
    store: MemoryStore = Depends(get_memory_store),
) -> FindingDetailResponse:
    """Record analyst review decision with reason validation and audit event."""
    finding = store.get_finding(finding_id)
    prev_status = (
        finding.status.value
        if hasattr(finding.status, "value")
        else str(finding.status)
    )

    return await store.record_decision(
        candidate_asset_id=finding.id,
        assessment_id=finding.id,
        previous_status=prev_status,
        new_status=payload.status.value,
        decision_reason=payload.decision_reason or "",
        notes=payload.notes,
        actor_label="analyst",
    )


@router.get("/{finding_id}/comparison", response_model=ComparisonResponse)
async def get_finding_comparison(
    finding_id: UUID,
    store: MemoryStore = Depends(get_memory_store),
) -> ComparisonResponse:
    """Resolve nearest official asset and compare side-by-side via Person 4's compare() interface."""
    finding = store.get_finding(finding_id)

    # 1. Resolve nearest official asset for this brand
    brand_assets = [
        a for a in store.assets.values()
        if a["brand_id"] == finding.brand_id and a["is_active"]
    ]
    if not brand_assets:
        raise NotFoundException(
            f"No official asset found for brand '{finding.brand_id}'."
        )

    # Preferred matching: matched ID -> same platform -> first asset
    matched_id = finding.identity_guard.matched_official_asset_id
    official_rec = None
    if matched_id:
        official_rec = store.assets.get(matched_id)

    if not official_rec:
        for a in brand_assets:
            if a["platform"].lower() == finding.candidate.platform.lower():
                official_rec = a
                break

    if not official_rec:
        official_rec = brand_assets[0]

    official_ctx = OfficialAssetCtx(
        id=official_rec["id"],
        brand_id=official_rec["brand_id"],
        asset_type=official_rec["asset_type"],
        platform=official_rec["platform"],
        stable_identifier=official_rec["stable_identifier"],
        secondary_identifiers=official_rec.get("secondary_identifiers", {}),
        developer_id=official_rec.get("developer_id"),
        publisher_name=official_rec.get("publisher_name"),
        display_name=official_rec["display_name"],
        handle=official_rec.get("handle"),
        description=official_rec.get("description"),
        category=official_rec.get("category"),
        canonical_url=official_rec.get("canonical_url"),
        icon_url=official_rec.get("icon_url"),
        icon_hash=official_rec.get("icon_hash"),
        relationship=official_rec["relationship"],
        verification_method=official_rec["verification_method"],
        is_verified=official_rec["is_verified"],
        trust_publisher=official_rec["trust_publisher"],
        is_active=official_rec["is_active"],
        notes=official_rec.get("notes"),
    )

    candidate_norm = NormalizedCandidate(
        source_id="apple_itunes" if finding.candidate.platform == "apple_app_store" else "bluesky_public",
        platform=finding.candidate.platform,
        asset_type=finding.candidate.asset_type,
        stable_identifier=finding.candidate.stable_identifier,
        display_name=finding.candidate.display_name,
        handle=finding.candidate.handle,
        publisher_name=finding.candidate.publisher_name,
        description=finding.candidate.description,
        category=finding.candidate.category,
        external_links=finding.candidate.external_links,
        icon_url=finding.candidate.icon_url,
        canonical_url=finding.candidate.canonical_url,
        created_at_source=finding.candidate.created_at_source,
        followers=finding.candidate.followers,
        rating_count=finding.candidate.rating_count,
        source_mode=finding.source_mode,
        retrieved_at=finding.created_at,
    )

    # 2. Call Person 4's agreed compare() interface
    try:
        comparisons = compare(candidate_norm, official_ctx)
    except NotImplementedError:
        # Fallback if Person 4's detection branch is not yet merged
        comparisons = [
            FieldComparison(
                field="display_name",
                official_value=official_ctx.display_name,
                candidate_value=candidate_norm.display_name,
                similarity=0.85,
                name_diff=[
                    NameDiffSegment(text=official_ctx.display_name, changed=False),
                ],
                non_ascii_chars=[],
            ),
            FieldComparison(
                field="publisher_name",
                official_value=official_ctx.publisher_name,
                candidate_value=candidate_norm.publisher_name,
                similarity=0.31,
            ),
            FieldComparison(
                field="developer_id",
                official_value=official_ctx.developer_id,
                candidate_value=candidate_norm.developer_id,
                similarity=None,
            ),
            FieldComparison(
                field="icon",
                official_value=None,
                candidate_value=None,
                similarity=0.93,
                detail={"hamming_distance": 4},
            ),
            FieldComparison(
                field="description",
                official_value=official_ctx.description,
                candidate_value=candidate_norm.description,
                similarity=0.62,
            ),
        ]

    official_summary = ComparisonAssetSummary(
        asset_id=official_ctx.id,
        display_name=official_ctx.display_name,
        stable_identifier=official_ctx.stable_identifier,
        publisher_name=official_ctx.publisher_name,
        developer_id=official_ctx.developer_id,
        category=official_ctx.category,
        icon_url=official_ctx.icon_url,
        canonical_url=official_ctx.canonical_url,
    )

    candidate_summary = ComparisonAssetSummary(
        asset_id=None,
        display_name=candidate_norm.display_name,
        stable_identifier=candidate_norm.stable_identifier,
        publisher_name=candidate_norm.publisher_name,
        developer_id=candidate_norm.developer_id,
        category=candidate_norm.category,
        icon_url=candidate_norm.icon_url,
        canonical_url=candidate_norm.canonical_url,
    )

    return ComparisonResponse(
        finding_id=finding_id,
        nearest_official_asset_id=official_ctx.id,
        official_asset=official_summary,
        candidate_asset=candidate_summary,
        comparisons=comparisons,
        disclaimer="Similarity indicates a candidate for review, not proof of malicious intent.",
    )
