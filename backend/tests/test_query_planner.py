"""Tests for Query Planner service per Sections 5.4, 12, and 18.3."""

from uuid import uuid4

import pytest

from backend.app.services.query_planner.models import (
    AssetType,
    BrandCtx,
    OfficialAssetCtx,
)
from backend.app.services.query_planner.planner import (
    HARD_MAX_QUERIES,
    plan_queries,
)


@pytest.fixture
def sample_brand():
    return BrandCtx(
        id=uuid4(),
        name="Kaveri Bank",
        keywords=["KaveriBank", "Kaveri Mobile"],
        distinctive_tokens=["kaveri"],
        generic_tokens_extra=["bank"],
        industry_category="Finance",
    )


@pytest.fixture
def sample_assets(sample_brand):
    return [
        OfficialAssetCtx(
            id=uuid4(),
            brand_id=sample_brand.id,
            asset_type=AssetType.IOS_APP,
            platform="apple_app_store",
            stable_identifier="1234567890",
            secondary_identifiers={"bundle_id": "com.kaveribank.mobile"},
            display_name="Kaveri Bank",
            developer_id="9000000001",
            is_active=True,
            is_verified=True,
        ),
        OfficialAssetCtx(
            id=uuid4(),
            brand_id=sample_brand.id,
            asset_type=AssetType.SOCIAL_ACCOUNT,
            platform="bluesky",
            stable_identifier="did:plc:kaveribank123",
            handle="kaveribank.bsky.social",
            display_name="Kaveri Bank Official",
            is_active=True,
            is_verified=True,
        ),
    ]


def test_query_planner_bounds_apple(sample_brand, sample_assets):
    """Verify Apple iTunes queries are bounded by default to at most 8."""
    plan = plan_queries(sample_brand, sample_assets, source_id="apple_itunes")
    assert len(plan.queries) <= 8
    assert len(plan.queries) > 0
    assert plan.brand_id == sample_brand.id


def test_query_planner_bounds_bluesky(sample_brand, sample_assets):
    """Verify Bluesky queries are bounded by default to at most 6."""
    plan = plan_queries(sample_brand, sample_assets, source_id="bluesky_public")
    assert len(plan.queries) <= 6
    assert len(plan.queries) > 0


def test_query_planner_hard_max(sample_brand, sample_assets):
    """Verify hard cap of 12 is never exceeded even if requested higher."""
    plan = plan_queries(sample_brand, sample_assets, source_id="apple_itunes", max_queries=50)
    assert len(plan.queries) <= HARD_MAX_QUERIES


def test_query_planner_ordering_and_kinds(sample_brand, sample_assets):
    """Verify priority sequence:
    1. BASE (brand name, keywords)
    2. SPACING ('kaveribank')
    3. SEPARATOR ('kaveri-bank', 'kaveri.bank')
    4. ADDED_WORD ('kaveri bank official', 'kaveri bank support', ...)
    5. DISTINCTIVE ('kaveri')
    """
    plan = plan_queries(sample_brand, sample_assets, source_id="apple_itunes", max_queries=12)
    terms = [q.term for q in plan.queries]
    kinds = [q.kind for q in plan.queries]

    # First query must be BASE (normalized brand name 'kaveri bank')
    assert kinds[0] == "BASE"
    assert terms[0] == "kaveri bank"

    # Spacing variant should appear
    assert "kaveribank" in terms
    idx_spacing = terms.index("kaveribank")
    assert kinds[idx_spacing] == "SPACING"

    # Priority numbers must be strictly increasing
    priorities = [q.priority for q in plan.queries]
    assert priorities == list(range(1, len(plan.queries) + 1))


def test_query_planner_deduplication(sample_brand):
    """Verify queries are deduplicated after normalization while preserving order."""
    brand_with_dups = BrandCtx(
        id=sample_brand.id,
        name="Kaveri Bank",
        keywords=["kaveri bank", "KAVERI BANK", "kaveribank"],
        distinctive_tokens=["kaveri"],
    )
    plan = plan_queries(brand_with_dups, [], source_id="apple_itunes", max_queries=12)
    terms = [q.term for q in plan.queries]
    assert len(terms) == len(set(terms)), f"Duplicate terms found in: {terms}"
