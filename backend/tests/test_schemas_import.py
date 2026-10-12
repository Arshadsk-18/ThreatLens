"""Tests ensuring clean import and integrity of all shared contract schemas.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 10-12
"""

import uuid
from datetime import datetime, timezone

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

import pytest

from app.repositories.base import (
    AssessmentRepo,
    AssetRepo,
    BrandRepo,
    CacheRepo,
    CandidateRepo,
    DecisionRepo,
    ScanRepo,
)
from app.schemas import (
    AssessmentResult,
    AssetType,
    BrandCtx,
    IdentityDecision,
    NormalizedCandidate,
    OfficialAssetCtx,
    PlannedQuery,
    QueryPlan,
    ScoringConfig,
    SourceMode,
    SourceResult,
    SourceStatus,
)
from app.services.assess import assess, compare, icon_similarity
from app.services.query_planner import plan_queries
from app.services.sources.base import SourceAdapter


def test_normalized_candidate_safe_defaults() -> None:
    """NormalizedCandidate must have safe default factories for mutable collections."""
    c1 = NormalizedCandidate(
        source_id="apple_itunes",
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier="12345",
        display_name="Kaveri Bank",
        source_mode=SourceMode.LIVE,
        retrieved_at=datetime.now(UTC),
    )
    c2 = NormalizedCandidate(
        source_id="bluesky_public",
        platform="bluesky",
        asset_type=AssetType.SOCIAL_ACCOUNT,
        stable_identifier="did:plc:test",
        display_name="Kaveri Bank",
        source_mode=SourceMode.LIVE,
        retrieved_at=datetime.now(UTC),
    )

    # Mutation on c1 must not affect c2
    c1.secondary_identifiers["bundle_id"] = "com.kaveri.bank"
    c1.external_links.append("https://kaveribank.example")
    c1.matched_queries.append("kaveri bank")

    assert c2.secondary_identifiers == {}
    assert c2.external_links == []
    assert c2.matched_queries == []


def test_query_plan_and_source_result() -> None:
    """QueryPlan and SourceResult models instantiate with contract-defined fields."""
    b_id = uuid.uuid4()
    plan = QueryPlan(
        brand_id=b_id,
        queries=[
            PlannedQuery(term="kaveri bank", kind="BASE", priority=1),
            PlannedQuery(term="kaveribank", kind="SPACING", priority=2),
        ],
    )
    assert plan.brand_id == b_id
    assert len(plan.queries) == 2

    res = SourceResult(
        source_id="apple_itunes",
        status=SourceStatus.CONNECTED,
        source_mode=SourceMode.LIVE,
        queries_executed=2,
    )
    assert res.source_id == "apple_itunes"
    assert res.candidates == []


def test_brand_and_official_asset_context() -> None:
    """BrandCtx and OfficialAssetCtx instantiate with correct types and defaults."""
    brand_id = uuid.uuid4()
    brand = BrandCtx(
        id=brand_id,
        name="Kaveri Bank",
        official_domains=["kaveribank.example"],
        distinctive_tokens=["kaveri"],
    )
    assert brand.name == "Kaveri Bank"
    assert brand.demo_brand is False

    asset = OfficialAssetCtx(
        id=uuid.uuid4(),
        brand_id=brand_id,
        asset_type=AssetType.IOS_APP,
        platform="apple_app_store",
        stable_identifier="1234567890",
        display_name="Kaveri Bank",
    )
    assert asset.relationship.value == "OFFICIAL"
    assert asset.is_verified is False


def test_scoring_and_assessment_models() -> None:
    """ScoringConfig, SignalResult, and AssessmentResult conform to Section 12."""
    config = ScoringConfig()
    assert config.scoring_version == "3.0.0"
    assert config.relevance_threshold == 0.60
    assert config.review_threshold == 25

    ar = AssessmentResult(
        identity_decision=IdentityDecision.OFFICIAL_EXACT_MATCH,
        rule="R1_EXACT_ID",
        explanation="Cleared by exact ID match.",
    )
    assert ar.identity_decision == IdentityDecision.OFFICIAL_EXACT_MATCH
    assert ar.scoring_version == "3.0.0"
    assert ar.relevant is True


def test_protocol_and_stubs_integrity() -> None:
    """Agreed teammate Protocol stubs raise NotImplementedError and are runtime checkable."""
    with pytest.raises(NotImplementedError):
        assess(None, None, None, None)  # type: ignore

    with pytest.raises(NotImplementedError):
        icon_similarity("abc", "def")

    with pytest.raises(NotImplementedError):
        compare(None, None)  # type: ignore

    with pytest.raises(NotImplementedError):
        plan_queries(None, None, "apple_itunes", 8)  # type: ignore

    # Check runtime protocol types
    assert isinstance(BrandRepo, type)
    assert isinstance(AssetRepo, type)
    assert isinstance(ScanRepo, type)
    assert isinstance(CandidateRepo, type)
    assert isinstance(AssessmentRepo, type)
    assert isinstance(DecisionRepo, type)
    assert isinstance(CacheRepo, type)
    assert isinstance(SourceAdapter, type)
