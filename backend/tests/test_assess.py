"""Unit tests for master assessment engine assess() per Sections 8.6, 8.7, and 18.3."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from backend.app.services.assess.engine import assess
from backend.app.services.query_planner.models import (
    AssetType,
    BrandCtx,
    IdentityDecision,
    OfficialAssetCtx,
    Relationship,
)
from backend.app.services.scoring.models import (
    NormalizedCandidate,
    Severity,
)


@pytest.fixture
def brand():
    return BrandCtx(
        id=uuid4(),
        name="Kaveri Bank",
        description="Official Kaveri Bank banking services and mobile app.",
        official_domains=["kaveribank.example"],
        keywords=["Kaveri Bank", "KaveriBank"],
        distinctive_tokens=["kaveri"],
        generic_tokens_extra=["bank"],
        industry_category="Finance",
    )


@pytest.fixture
def official_app(brand):
    return OfficialAssetCtx(
        id=uuid4(),
        brand_id=brand.id,
        asset_type=AssetType.IOS_APP,
        platform="apple_app_store",
        stable_identifier="1234567890",
        secondary_identifiers={"bundle_id": "com.kaveribank.mobile"},
        developer_id="9000000001",
        publisher_name="Kaveri Bank Ltd",
        display_name="Kaveri Bank",
        description="Official Kaveri Bank banking application with secure accounts.",
        canonical_url="https://apps.apple.com/app/id1234567890",
        icon_hash="a1b2c3d4e5f60718",
        relationship=Relationship.OFFICIAL,
        is_verified=True,
        is_active=True,
        trust_publisher=True,
    )


@pytest.fixture
def official_social(brand):
    return OfficialAssetCtx(
        id=uuid4(),
        brand_id=brand.id,
        asset_type=AssetType.SOCIAL_ACCOUNT,
        platform="bluesky",
        stable_identifier="did:plc:kaveribank123",
        handle="kaveribank.bsky.social",
        display_name="Kaveri Bank Official",
        description="Official customer updates and support for Kaveri Bank.",
        icon_hash="1122334455667788",
        relationship=Relationship.OFFICIAL,
        is_verified=True,
        is_active=True,
    )


# -------------------------------------------------------------
# 1. Worked examples from Section 8.6
# -------------------------------------------------------------

def test_section_8_6_official_exact_match(brand, official_app):
    """Candidate bundle ID equals registered official bundle ID -> OFFICIAL_EXACT_MATCH."""
    cand = NormalizedCandidate(
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier="1234567890",
        secondary_identifiers={"bundle_id": "com.kaveribank.mobile"},
        display_name="Kaveri Bank",
    )
    res = assess(cand, brand, [official_app])
    assert res.identity_decision == IdentityDecision.OFFICIAL_EXACT_MATCH
    assert res.rule == "R1_EXACT_ID"
    assert res.matched_official_asset_id == official_app.id


def test_section_8_6_official_publisher_match(brand, official_app):
    """Another app by the registered developer ID -> OFFICIAL_PUBLISHER_MATCH."""
    cand = NormalizedCandidate(
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier="9999999999",
        developer_id="9000000001",
        display_name="Kaveri Wealth",
    )
    res = assess(cand, brand, [official_app])
    assert res.identity_decision == IdentityDecision.OFFICIAL_PUBLISHER_MATCH
    assert res.rule == "R2_PUBLISHER_ID"


def test_section_8_6_benign_namesake_kaveri_coffee_roasters(brand, official_app):
    """'Kaveri Coffee Roasters' (Food & Drink) passes G1 (>= 0.60); no corroborating groups; category mismatch -> BENIGN_LOOKALIKE."""
    cand = NormalizedCandidate(
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier="7777777777",
        developer_id="9999999999",
        publisher_name="Roasters Ltd",
        display_name="Kaveri Coffee Roasters",
        category="Food & Drink",
        description="Artisan coffee roasted locally in our cafe.",
    )
    res = assess(cand, brand, [official_app])
    assert res.identity_decision == IdentityDecision.BENIGN_LOOKALIKE
    assert res.rule == "G4_UNRELATED_CATEGORY"
    assert res.risk_score <= 24


def test_namesake_not_flagged(brand, official_app):
    """Verify unrelated namesake is never a CANDIDATE_FOR_REVIEW finding."""
    cand = NormalizedCandidate(
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier="7777777777",
        display_name="Kaveri Coffee Roasters",
        category="Food & Drink",
        description="Artisan coffee roaster beans and mugs.",
    )
    res = assess(cand, brand, [official_app])
    assert res.identity_decision == IdentityDecision.BENIGN_LOOKALIKE


def test_section_8_6_name_only_capped_at_medium(brand, official_app):
    """Exact name 'Kaveri Bank' by different developer with nothing else observable -> CANDIDATE_FOR_REVIEW, MEDIUM (cap 49)."""
    cand = NormalizedCandidate(
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier="8888888888",
        developer_id="9999999999",
        display_name="Kaveri Bank",
    )
    res = assess(cand, brand, [official_app])
    assert res.identity_decision == IdentityDecision.CANDIDATE_FOR_REVIEW
    assert res.severity == Severity.MEDIUM
    assert res.risk_score <= 49


# -------------------------------------------------------------
# 2. Section 8.7 Walkthrough Scenarios
# -------------------------------------------------------------

def test_scenario_a_fake_app(brand, official_app):
    """Scenario A: fake app 'Kaveri Bank Rewards' with copied icon, description, seller link, young age, lure terms."""
    cand = NormalizedCandidate(
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier="9876543210",
        developer_id="9000000042",
        publisher_name="KB Rewards Studio",
        display_name="Kaveri Bank Rewards",
        category="Finance",
        icon_hash=official_app.icon_hash,  # exact icon hash (similarity 1.0)
        description=official_app.description,  # copied description
        external_links=["https://kb-rewards.example"],  # non-official link
        created_at_source=datetime.now(UTC) - timedelta(days=21),
        rating_count=12,
    )
    res = assess(cand, brand, [official_app])
    assert res.identity_decision == IdentityDecision.CANDIDATE_FOR_REVIEW
    assert res.severity in (Severity.HIGH, Severity.CRITICAL)
    assert len(res.corroborating_groups) >= 2


def test_scenario_b_honest_fan_page(brand, official_social):
    """Scenario B: Bluesky 'Kaveri Bank Fans', 400 days old, bio 'Unofficial fan page, not affiliated.'
    Outcome: BENIGN_LOOKALIKE, G4_LOW_CONTENT_OVERLAP, shown <= 24.
    """
    cand = NormalizedCandidate(
        platform="bluesky",
        asset_type=AssetType.SOCIAL_ACCOUNT,
        stable_identifier="did:plc:fan123",
        handle="kaverifans.bsky.social",
        display_name="Kaveri Bank Fans",
        description="Unofficial fan page, not affiliated.",
        created_at_source=datetime.now(UTC) - timedelta(days=400),
        followers=2300,
        posts_count=900,
    )
    res = assess(cand, brand, [official_social])
    assert res.identity_decision == IdentityDecision.BENIGN_LOOKALIKE
    assert res.rule in ("G4_LOW_CONTENT_OVERLAP", "G5_DECLARED_UNOFFICIAL")
    assert res.risk_score <= 24


def test_scenario_c_fan_page_quoting_brand(brand, official_social):
    """Scenario C: Quotes brand text, bio overlap >= 0.20, disclaimer present, all 4 G5 safeguards hold -> G5_DECLARED_UNOFFICIAL."""
    cand = NormalizedCandidate(
        platform="bluesky",
        asset_type=AssetType.SOCIAL_ACCOUNT,
        stable_identifier="did:plc:fan456",
        handle="kaverifans.bsky.social",
        display_name="Kaveri Bank Fans",
        description="Unofficial fan page, not affiliated. Official customer updates and support for Kaveri Bank.",
        created_at_source=datetime.now(UTC) - timedelta(days=400),
        followers=2300,
        posts_count=900,
    )
    res = assess(cand, brand, [official_social])
    assert res.identity_decision == IdentityDecision.BENIGN_LOOKALIKE
    assert res.risk_score <= 24


def test_scenario_d_quiet_attacker_copied_avatar(brand, official_social):
    """Scenario D: Quiet attacker with disclaimer but copied avatar -> G5 SKIPPED because VISUAL fired. Outcome: CANDIDATE_FOR_REVIEW."""
    cand = NormalizedCandidate(
        platform="bluesky",
        asset_type=AssetType.SOCIAL_ACCOUNT,
        stable_identifier="did:plc:attacker123",
        handle="kaverifans.bsky.social",
        display_name="Kaveri Bank Fans",
        description="Unofficial fan page, not affiliated.",
        icon_hash=official_social.icon_hash,  # copied avatar!
        created_at_source=datetime.now(UTC) - timedelta(days=9),
        followers=25,
        posts_count=4,
    )
    res = assess(cand, brand, [official_social])
    assert res.identity_decision == IdentityDecision.CANDIDATE_FOR_REVIEW
    assert "G5_DECLARED_UNOFFICIAL" not in res.gates_applied


def test_scenario_e_loud_attacker(brand, official_social):
    """Scenario E: Loud attacker with lure terms, mismatching link, copied avatar -> CANDIDATE_FOR_REVIEW, CRITICAL."""
    cand = NormalizedCandidate(
        platform="bluesky",
        asset_type=AssetType.SOCIAL_ACCOUNT,
        stable_identifier="did:plc:loud123",
        handle="kavericare.bsky.social",
        display_name="Kaveri Bank Care",
        description="unofficial, plus customer care, KYC update and rewards",
        icon_hash=official_social.icon_hash,
        external_links=["https://short.url/fake"],
        created_at_source=datetime.now(UTC) - timedelta(days=12),
        followers=40,
        posts_count=3,
    )
    res = assess(cand, brand, [official_social])
    assert res.identity_decision == IdentityDecision.CANDIDATE_FOR_REVIEW
    assert res.risk_score >= 70
    assert res.severity in (Severity.HIGH, Severity.CRITICAL)


# -------------------------------------------------------------
# 3. Safeguard Specific Tests (Section 8.4a)
# -------------------------------------------------------------

def test_declared_unofficial_cannot_hide_copied_avatar(brand, official_social):
    """G5 safeguard 3: Copied avatar cancels G5 exemption."""
    cand = NormalizedCandidate(
        platform="bluesky",
        asset_type=AssetType.SOCIAL_ACCOUNT,
        stable_identifier="did:plc:avatar_abuse",
        display_name="Kaveri Bank Community",
        description="Unofficial fan page, not affiliated.",
        icon_hash=official_social.icon_hash,
    )
    res = assess(cand, brand, [official_social])
    assert res.identity_decision == IdentityDecision.CANDIDATE_FOR_REVIEW
    assert res.rule != "G5_DECLARED_UNOFFICIAL"


def test_declared_unofficial_requires_clean_lure_and_links(brand, official_social):
    """G5 safeguard 2: Presence of lure terms or mismatching link cancels G5 exemption."""
    cand_lures = NormalizedCandidate(
        platform="bluesky",
        asset_type=AssetType.SOCIAL_ACCOUNT,
        stable_identifier="did:plc:lure_abuse",
        display_name="Kaveri Bank Community",
        description="Unofficial fan page! Get instant loan and reward here.",
    )
    res = assess(cand_lures, brand, [official_social])
    assert res.rule != "G5_DECLARED_UNOFFICIAL"

    cand_link = NormalizedCandidate(
        platform="bluesky",
        asset_type=AssetType.SOCIAL_ACCOUNT,
        stable_identifier="did:plc:link_abuse",
        display_name="Kaveri Bank Community",
        description="Unofficial fan page, not affiliated.",
        external_links=["https://phishing-site.example/login"],
    )
    res_link = assess(cand_link, brand, [official_social])
    assert res_link.rule != "G5_DECLARED_UNOFFICIAL"


def test_g5_never_applies_to_exact_name_or_homoglyph(brand, official_social):
    """G5 safeguard 4: EXACT_NAME_REUSE or HOMOGLYPH cancels G5 exemption."""
    cand_exact = NormalizedCandidate(
        platform="bluesky",
        asset_type=AssetType.SOCIAL_ACCOUNT,
        stable_identifier="did:plc:exact_abuse",
        display_name="Kaveri Bank",  # Exact name!
        description="Unofficial parody account.",
    )
    res_exact = assess(cand_exact, brand, [official_social])
    assert res_exact.rule != "G5_DECLARED_UNOFFICIAL"

    cand_homo = NormalizedCandidate(
        platform="bluesky",
        asset_type=AssetType.SOCIAL_ACCOUNT,
        stable_identifier="did:plc:homo_abuse",
        display_name="Kaver\u0456 Bank",  # Cyrillic homoglyph!
        description="Unofficial fan account.",
    )
    res_homo = assess(cand_homo, brand, [official_social])
    assert res_homo.rule != "G5_DECLARED_UNOFFICIAL"
