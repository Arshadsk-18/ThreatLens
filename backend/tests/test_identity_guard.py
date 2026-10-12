"""Tests for IdentityGuard service per Section 7 and Section 18.3."""

from uuid import uuid4

import pytest

from backend.app.services.identity_guard.guard import (
    CandidateInput,
    evaluate_identity_guard,
)
from backend.app.services.query_planner.models import (
    AssetType,
    BrandCtx,
    IdentityDecision,
    OfficialAssetCtx,
    Relationship,
)


@pytest.fixture
def brand():
    return BrandCtx(
        id=uuid4(),
        name="Kaveri Bank",
        distinctive_tokens=["kaveri"],
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
        relationship=Relationship.OFFICIAL,
        is_verified=True,
        is_active=True,
    )


@pytest.fixture
def authorized_partner(brand):
    return OfficialAssetCtx(
        id=uuid4(),
        brand_id=brand.id,
        asset_type=AssetType.IOS_APP,
        platform="apple_app_store",
        stable_identifier="5555555555",
        secondary_identifiers={"bundle_id": "com.partner.kaveripay"},
        developer_id="9000000088",
        publisher_name="Authorized FinTech Partner Ltd",
        display_name="Kaveri Pay by Partner",
        relationship=Relationship.AUTHORIZED_PARTNER,
        is_verified=True,
        is_active=True,
    )


def test_official_app_never_flagged(brand, official_app):
    """Must-pass automated test: exact trackId or bundle_id matches R1_EXACT_ID."""
    # Match by stable_identifier (trackId)
    cand_by_track = CandidateInput(
        platform="apple_app_store",
        stable_identifier="1234567890",
        display_name="Kaveri Bank",
    )
    res1 = evaluate_identity_guard(cand_by_track, brand, [official_app])
    assert res1 is not None
    assert res1.decision == IdentityDecision.OFFICIAL_EXACT_MATCH
    assert res1.rule == "R1_EXACT_ID"
    assert res1.matched_official_asset_id == official_app.id

    # Match by secondary_identifier bundle_id
    cand_by_bundle = CandidateInput(
        platform="apple_app_store",
        stable_identifier="9999999999",  # different trackId
        secondary_identifiers={"bundle_id": "com.kaveribank.mobile"},
        display_name="Kaveri Bank",
    )
    res2 = evaluate_identity_guard(cand_by_bundle, brand, [official_app])
    assert res2 is not None
    assert res2.decision == IdentityDecision.OFFICIAL_EXACT_MATCH
    assert res2.rule == "R1_EXACT_ID"
    assert res2.matched_official_asset_id == official_app.id


def test_official_social_never_flagged(brand, official_social):
    """Must-pass automated test: exact DID or handle matches R1_EXACT_ID."""
    # Match by DID
    cand_did = CandidateInput(
        platform="bluesky",
        stable_identifier="did:plc:kaveribank123",
        display_name="Kaveri Bank Official",
    )
    res1 = evaluate_identity_guard(cand_did, brand, [official_social])
    assert res1 is not None
    assert res1.decision == IdentityDecision.OFFICIAL_EXACT_MATCH
    assert res1.rule == "R1_EXACT_ID"
    assert res1.matched_official_asset_id == official_social.id

    # Match by handle
    cand_handle = CandidateInput(
        platform="bluesky",
        stable_identifier="did:plc:unknown999",
        handle="kaveribank.bsky.social",
        display_name="Kaveri Bank",
    )
    res2 = evaluate_identity_guard(cand_handle, brand, [official_social])
    assert res2 is not None
    assert res2.decision == IdentityDecision.OFFICIAL_EXACT_MATCH
    assert res2.rule == "R1_EXACT_ID"
    assert res2.matched_official_asset_id == official_social.id


def test_publisher_id_clears_second_app(brand, official_app):
    """Must-pass automated test: R2_PUBLISHER_ID clears second app by registered developer_id."""
    second_app = CandidateInput(
        platform="apple_app_store",
        stable_identifier="8888888888",
        developer_id="9000000001",  # Same developer_id as official_app
        display_name="Kaveri Wealth Management",
        publisher_name="Kaveri Bank Ltd",
    )
    res = evaluate_identity_guard(second_app, brand, [official_app])
    assert res is not None
    assert res.decision == IdentityDecision.OFFICIAL_PUBLISHER_MATCH
    assert res.rule == "R2_PUBLISHER_ID"
    assert res.matched_official_asset_id == official_app.id

    # If trust_publisher is False on the official asset, it must NOT clear on developer_id
    untrusted_official = official_app.model_copy(update={"trust_publisher": False})
    res_untrusted = evaluate_identity_guard(second_app, brand, [untrusted_official])
    assert res_untrusted is None


def test_authorized_partner_match(brand, authorized_partner):
    """R3_PARTNER matches partner assets."""
    cand_partner = CandidateInput(
        platform="apple_app_store",
        stable_identifier="5555555555",
        display_name="Kaveri Pay by Partner",
    )
    res = evaluate_identity_guard(cand_partner, brand, [authorized_partner])
    assert res is not None
    assert res.decision == IdentityDecision.AUTHORIZED_PARTNER_MATCH
    assert res.rule == "R3_PARTNER"
    assert res.matched_official_asset_id == authorized_partner.id


def test_name_and_publisher_string_alone_never_clear(brand, official_app):
    """Strict invariant: Never clear on name, publisher name string, logo or description alone."""
    # Impersonator copying exact name and publisher string, but different developer_id and trackId
    impersonator = CandidateInput(
        platform="apple_app_store",
        stable_identifier="6666666666",  # different trackId
        developer_id="9999999999",       # different developerId
        secondary_identifiers={"bundle_id": "com.fraud.kaveribank"},
        display_name="Kaveri Bank",       # exact same name!
        publisher_name="Kaveri Bank Ltd", # exact same publisher name!
        description="Official Kaveri Bank mobile application",
    )
    res = evaluate_identity_guard(impersonator, brand, [official_app])
    # Must NOT clear: returns None to proceed to scoring
    assert res is None, "Impersonator with matching name/publisher was cleared incorrectly!"
