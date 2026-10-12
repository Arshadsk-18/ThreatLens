"""Health, readiness, and metadata endpoints.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.1
"""

from fastapi import APIRouter

from app.core import scoring_config
from app.core.config import settings
from app.schemas.enums import (
    ApiErrorCode,
    AssetType,
    EvalLabel,
    EvalProvenance,
    EvalSplit,
    EvidenceGroup,
    EvidenceStatus,
    FindingStatus,
    IdentityDecision,
    LookalikeTechnique,
    ProviderErrorCode,
    Relationship,
    ScanMode,
    ScanStage,
    ScanStatus,
    Severity,
    SourceId,
    SourceMode,
    SourceStatus,
    VerificationMethod,
)
from app.schemas.health import HealthResponse, ReadyResponse
from app.schemas.meta import MetaResponse

router = APIRouter(tags=["Health & Meta"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Service liveness probe."""
    return HealthResponse(
        status="ok",
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        contract_version=settings.CONTRACT_VERSION,
    )


@router.get("/ready", response_model=ReadyResponse)
async def get_ready() -> ReadyResponse:
    """Service readiness probe verifying essential subsystems (no secrets exposed)."""
    return ReadyResponse(
        ready=True,
        checks={"database": "ok", "config": "ok"},
    )


@router.get("/meta", response_model=MetaResponse)
async def get_meta() -> MetaResponse:
    """System metadata, enum catalog, scoring thresholds, and supported platforms."""
    all_enums = {
        "ScanMode": [e.value for e in ScanMode],
        "SourceMode": [e.value for e in SourceMode],
        "SourceStatus": [e.value for e in SourceStatus],
        "ScanStatus": [e.value for e in ScanStatus],
        "ScanStage": [e.value for e in ScanStage],
        "AssetType": [e.value for e in AssetType],
        "Relationship": [e.value for e in Relationship],
        "VerificationMethod": [e.value for e in VerificationMethod],
        "IdentityDecision": [e.value for e in IdentityDecision],
        "Severity": [e.value for e in Severity],
        "FindingStatus": [e.value for e in FindingStatus],
        "EvidenceStatus": [e.value for e in EvidenceStatus],
        "EvidenceGroup": [e.value for e in EvidenceGroup],
        "LookalikeTechnique": [e.value for e in LookalikeTechnique],
        "ProviderErrorCode": [e.value for e in ProviderErrorCode],
        "ApiErrorCode": [e.value for e in ApiErrorCode],
        "EvalLabel": [e.value for e in EvalLabel],
        "EvalProvenance": [e.value for e in EvalProvenance],
        "EvalSplit": [e.value for e in EvalSplit],
        "SourceId": [e.value for e in SourceId],
    }

    thresholds = {
        "relevance": scoring_config.RELEVANCE_THRESHOLD,
        "review": scoring_config.REVIEW_THRESHOLD,
        "severity_bands": scoring_config.SEVERITY_BANDS,
        "g2_corroborating_groups_min": scoring_config.G2_MIN_CORROBORATING_GROUPS,
        "g3_evidence_coverage_min": scoring_config.G3_MIN_EVIDENCE_COVERAGE,
        "g4_low_content_overlap_threshold": scoring_config.G4_LOW_CONTENT_OVERLAP_THRESHOLD,
    }

    return MetaResponse(
        scoring_version=scoring_config.SCORING_VERSION,
        contract_version=settings.CONTRACT_VERSION,
        enums=all_enums,
        thresholds=thresholds,
        signal_tables=scoring_config.SIGNAL_TABLES,
        supported_platforms=scoring_config.SUPPORTED_PLATFORMS,
        supported_asset_types=scoring_config.SUPPORTED_ASSET_TYPES,
    )
