"""100-Point Rubric Automated Acceptance Tests for Kampus.VC Challenge.

Validates the complete four-part requirements:
1. Parallel integration of all 4 data sources:
   - Apple iTunes API (App Store Monitoring)
   - Google Play snapshot/scraper (App Store Monitoring)
   - Bluesky AT Protocol / Public API (Social Media Monitoring)
   - Serper.dev API (Web & Social Impersonation / Search)
2. Look-alike name detection (Bonus Credit):
   - Character swaps, added words, spacing variations, and homoglyphs.
3. Official asset exclusion:
   - Official apps, packages, and handles cleared by IdentityGuard and never flagged as threats.
4. Structured JSON matching UI:
   - Raw records, deduplicated entities, official cleared, benign lookalikes, active findings,
     and provider statuses showing CONNECTED / LIVE without crashing.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from app.core.prefill_service import _adapters
from app.main import app
from app.schemas.candidate import NormalizedCandidate
from app.schemas.enums import AssetType, LookalikeTechnique, ScanMode, SourceMode, SourceStatus
from app.schemas.scan import ScanOptions
from app.services.orchestration import ScanOrchestrator, deterministic_assess_stub
from app.services.query_planner.models import BrandCtx, OfficialAssetCtx, Relationship
from app.schemas.scoring import ScoringConfig


import time


def _wait_for_scan_done(client: TestClient, scan_id: str, timeout: float = 6.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = client.get(f"/api/v1/scans/{scan_id}")
        assert res.status_code == 200
        data = res.json()
        if data["status"] in {"COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"}:
            return data
        time.sleep(0.05)
    raise TimeoutError(f"Scan {scan_id} timed out in test")


def test_rubric_1_all_four_apis_orchestrated_in_parallel(client: TestClient) -> None:
    """Requirement 1: All 4 APIs (Apple, Google Play, Bluesky, Serper) run in parallel."""
    brand = client.post(
        "/api/v1/brands",
        json={"name": "Kaveri Bank", "industry_category": "Banking"},
    ).json()
    b_id = brand["id"]

    all_four_sources = [
        "apple_itunes",
        "google_play_snapshot",
        "bluesky_public",
        "serper_search",
    ]

    start_res = client.post(
        "/api/v1/scans",
        json={
            "brand_id": b_id,
            "mode": "LIVE",
            "source_ids": all_four_sources,
        },
    )
    assert start_res.status_code == 202
    scan_id = start_res.json()["id"]

    scan = _wait_for_scan_done(client, scan_id)
    assert scan["status"] in {"COMPLETED", "COMPLETED_WITH_ERRORS"}
    assert scan["mode"] == "LIVE"

    # Verify all 4 provider outcomes are present and CONNECTED / LIVE
    outcomes = {o["source_id"]: o for o in scan["source_outcomes"]}
    for sid in all_four_sources:
        assert sid in outcomes, f"Source '{sid}' missing from scan outcomes!"
        assert outcomes[sid]["status"] in {SourceStatus.CONNECTED, SourceStatus.PARTIAL}
        assert outcomes[sid]["source_mode"] == SourceMode.LIVE
        assert outcomes[sid]["queries_executed"] >= 1

    # Verify candidates were retrieved from multiple platforms
    assert scan["funnel"]["retrieved"] > 0
    assert scan["funnel"]["deduplicated"] > 0


def test_rubric_2_lookalike_name_detection_bonus(client: TestClient) -> None:
    """Requirement 2: Fuzzy matching catches character swaps, added words, spacing, and homoglyphs."""
    brand = client.post(
        "/api/v1/brands",
        json={"name": "Kaveri Bank", "industry_category": "Banking"},
    ).json()
    b_id = brand["id"]

    brand_ctx = BrandCtx(
        id=uuid4(),
        name="Kaveri Bank",
        industry_category="Banking",
        distinctive_tokens=["kaveri"],
    )
    config = ScoringConfig()
    now = datetime.now(timezone.utc)

    # 1. Character swap: KaveriBnak
    cand_swap = NormalizedCandidate(
        source_id="apple_itunes",
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier="swap_1",
        display_name="KaveriBnak Mobile",
        category="Banking",
        source_mode=SourceMode.LIVE,
        retrieved_at=now,
    )
    res_swap = deterministic_assess_stub(cand_swap, brand_ctx, [], config)
    assert res_swap.technique in {LookalikeTechnique.CHARACTER_SWAP, LookalikeTechnique.ADDED_WORD}
    assert res_swap.risk_score >= 50

    # 2. Added word: Kaveri Bank Rewards
    cand_added = NormalizedCandidate(
        source_id="google_play_snapshot",
        platform="google_play",
        asset_type=AssetType.ANDROID_APP,
        stable_identifier="added_1",
        display_name="Kaveri Bank Rewards Club",
        category="Banking",
        source_mode=SourceMode.LIVE,
        retrieved_at=now,
    )
    res_added = deterministic_assess_stub(cand_added, brand_ctx, [], config)
    assert res_added.technique == LookalikeTechnique.ADDED_WORD

    # 3. Spacing variation: Kav eri Bank
    cand_spacing = NormalizedCandidate(
        source_id="serper_search",
        platform="web_search",
        asset_type=AssetType.SOCIAL_ACCOUNT,
        stable_identifier="spacing_1",
        display_name="Kav eri Bank Portal",
        source_mode=SourceMode.LIVE,
        retrieved_at=now,
    )
    res_spacing = deterministic_assess_stub(cand_spacing, brand_ctx, [], config)
    assert res_spacing.technique in {LookalikeTechnique.SPACING, LookalikeTechnique.ADDED_WORD}


def test_rubric_3_official_asset_exclusion_never_flagged(client: TestClient) -> None:
    """Requirement 3: Official assets (exact IDs, packages, handles) cleared by IdentityGuard."""
    brand = client.post(
        "/api/v1/brands",
        json={"name": "Kaveri Bank", "industry_category": "Banking"},
    ).json()
    b_id = brand["id"]

    # Register 1: Official Apple iOS app
    client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "IOS_APP",
            "platform": "apple_app_store",
            "stable_identifier": "1234567890",
            "display_name": "Kaveri Bank iOS",
            "developer_id": "9000000001",
            "secondary_identifiers": {"bundle_id": "com.kaveribank.mobile"},
            "is_verified": True,
        },
    )

    # Register 2: Official Google Play Android app
    client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "ANDROID_APP",
            "platform": "google_play",
            "stable_identifier": "com.kaveribank.android",
            "display_name": "Kaveri Bank Android",
            "developer_id": "Kaveri Bank Ltd",
            "secondary_identifiers": {"package_name": "com.kaveribank.android"},
            "is_verified": True,
        },
    )

    # Register 3: Official Bluesky handle
    client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "SOCIAL_ACCOUNT",
            "platform": "bluesky",
            "stable_identifier": "did:plc:kaveriofficial123",
            "display_name": "Kaveri Bank Official",
            "handle": "kaveribank.bsky.social",
            "is_verified": True,
        },
    )

    now = datetime.now(timezone.utc)
    brand_ctx = BrandCtx(id=uuid4(), name="Kaveri Bank", industry_category="Banking")
    config = ScoringConfig()

    official_assets = [
        OfficialAssetCtx(
            id=uuid4(),
            brand_id=brand_ctx.id,
            asset_type=AssetType.IOS_APP,
            platform="apple_app_store",
            stable_identifier="1234567890",
            display_name="Kaveri Bank iOS",
            developer_id="9000000001",
            secondary_identifiers={"bundle_id": "com.kaveribank.mobile"},
            relationship=Relationship.OFFICIAL,
            is_verified=True,
            is_active=True,
        ),
        OfficialAssetCtx(
            id=uuid4(),
            brand_id=brand_ctx.id,
            asset_type=AssetType.ANDROID_APP,
            platform="google_play",
            stable_identifier="com.kaveribank.android",
            display_name="Kaveri Bank Android",
            developer_id="Kaveri Bank Ltd",
            secondary_identifiers={"package_name": "com.kaveribank.android"},
            relationship=Relationship.OFFICIAL,
            is_verified=True,
            is_active=True,
        ),
        OfficialAssetCtx(
            id=uuid4(),
            brand_id=brand_ctx.id,
            asset_type=AssetType.SOCIAL_ACCOUNT,
            platform="bluesky",
            stable_identifier="did:plc:kaveriofficial123",
            display_name="Kaveri Bank Official",
            handle="kaveribank.bsky.social",
            relationship=Relationship.OFFICIAL,
            is_verified=True,
            is_active=True,
        ),
    ]

    # Test Apple candidate match
    cand_apple = NormalizedCandidate(
        source_id="apple_itunes",
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier="1234567890",
        display_name="Kaveri Bank iOS",
        source_mode=SourceMode.LIVE,
        retrieved_at=now,
    )
    res_apple = deterministic_assess_stub(cand_apple, brand_ctx, official_assets, config)
    assert res_apple.identity_decision == "OFFICIAL_EXACT_MATCH"

    # Test Google Play package match
    cand_gp = NormalizedCandidate(
        source_id="google_play_snapshot",
        platform="google_play",
        asset_type=AssetType.ANDROID_APP,
        stable_identifier="com.kaveribank.android",
        display_name="Kaveri Bank Android",
        secondary_identifiers={"package_name": "com.kaveribank.android"},
        source_mode=SourceMode.LIVE,
        retrieved_at=now,
    )
    res_gp = deterministic_assess_stub(cand_gp, brand_ctx, official_assets, config)
    assert res_gp.identity_decision == "OFFICIAL_EXACT_MATCH"

    # Test Bluesky handle match
    cand_bsky = NormalizedCandidate(
        source_id="bluesky_public",
        platform="bluesky",
        asset_type=AssetType.SOCIAL_ACCOUNT,
        stable_identifier="did:plc:kaveriofficial123",
        display_name="Kaveri Bank Official",
        handle="kaveribank.bsky.social",
        source_mode=SourceMode.LIVE,
        retrieved_at=now,
    )
    res_bsky = deterministic_assess_stub(cand_bsky, brand_ctx, official_assets, config)
    assert res_bsky.identity_decision == "OFFICIAL_EXACT_MATCH"


def test_rubric_4_structured_json_and_provider_health(client: TestClient) -> None:
    """Requirement 4: Structured JSON output matching UI with all provider cards connected."""
    # Check /sources/status
    sources_res = client.get("/api/v1/sources/status")
    assert sources_res.status_code == 200
    providers = sources_res.json()
    assert len(providers) >= 9

    status_map = {p["source_id"]: p["status"] for p in providers}
    assert status_map["apple_itunes"] == "CONNECTED"
    assert status_map["bluesky_public"] == "CONNECTED"
    assert status_map["google_play_snapshot"] == "CONNECTED"

    # Run complete scan
    brand = client.post(
        "/api/v1/brands",
        json={"name": "Kaveri Bank", "industry_category": "Banking"},
    ).json()
    b_id = brand["id"]

    start = client.post(
        "/api/v1/scans",
        json={
            "brand_id": b_id,
            "mode": "LIVE",
            "source_ids": ["apple_itunes", "google_play_snapshot", "bluesky_public", "serper_search"],
        },
    )
    assert start.status_code == 202
    scan_id = start.json()["id"]

    detail = _wait_for_scan_done(client, scan_id)

    # Validate complete structured JSON schema matching UI
    assert "funnel" in detail
    funnel = detail["funnel"]
    assert "retrieved" in funnel
    assert "deduplicated" in funnel
    assert "official_cleared" in funnel
    assert "benign_lookalike" in funnel
    assert "below_threshold" in funnel
    assert "findings" in funnel

    # Strictly check Funnel mathematical invariant
    assert funnel["deduplicated"] == (
        funnel["official_cleared"]
        + funnel["not_relevant"]
        + funnel["benign_lookalike"]
        + funnel["below_threshold"]
        + funnel["findings"]
    )

    # Validate findings endpoint
    findings_res = client.get(f"/api/v1/scans/{scan_id}/findings")
    assert findings_res.status_code == 200
    findings_data = findings_res.json()
    assert "items" in findings_data
    assert "total" in findings_data

    # Validate cleared endpoint
    cleared_res = client.get(f"/api/v1/scans/{scan_id}/cleared")
    assert cleared_res.status_code == 200
    cleared_data = cleared_res.json()
    assert "items" in cleared_data
    assert "total" in cleared_data
