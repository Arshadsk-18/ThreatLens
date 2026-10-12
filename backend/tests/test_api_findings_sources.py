"""Comprehensive integration tests for P0 review and source-status routes.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 11.1, 11.2, 11.5
"""

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.memory_store import get_memory_store
from app.core.prefill_service import register_source_adapter
from app.schemas.asset import OfficialAssetCreate
from app.schemas.brand import BrandCreate
from app.schemas.candidate import NormalizedCandidate
from app.schemas.comparison import FieldComparison, NameDiffSegment, NonAsciiChar
from app.schemas.context import OfficialAssetCtx
from app.schemas.enums import (
    ApiErrorCode,
    AssetType,
    FindingStatus,
    IdentityDecision,
    LookalikeTechnique,
    Relationship,
    ScanMode,
    ScanStatus,
    Severity,
    SourceMode,
    SourceStatus,
    VerificationMethod,
)
from app.schemas.finding import (
    CandidateSummary,
    ClearedCandidateSummary,
    ClearedListItem,
    FindingDetailCandidate,
    FindingDetailResponse,
    FindingListItem,
    IdentityGuardResult,
    TopSignal,
)
from app.schemas.scan import ScanFunnel, ScanOptions, SourceOutcome
from app.schemas.source import SourceHealth
from app.services.sources.base import SourceAdapter


@pytest.fixture(autouse=True)
def clean_memory_store():
    """Ensure in-memory store is reset for each test."""
    store = get_memory_store()
    store.clear()
    yield
    store.clear()


def seed_brand_with_assets_and_findings(store):
    """Helper to seed brand, official asset, scans, findings, and cleared items."""
    now = datetime.now(timezone.utc)

    # 1. Create brand
    b_resp = store.create_brand(
        BrandCreate(
            name="Kaveri Bank",
            description="Fictional demo bank",
            official_domains=["kaveribank.example"],
            keywords=["Kaveri Bank", "KaveriBank"],
            distinctive_tokens=["kaveri"],
            industry_category="Finance",
            demo_brand=True,
        )
    )
    brand_id = b_resp.id

    # 2. Register official asset
    a_resp = store.create_asset(
        brand_id=brand_id,
        data=OfficialAssetCreate(
            asset_type=AssetType.IOS_APP,
            platform="apple_app_store",
            stable_identifier="1234567890",
            developer_id="9000000001",
            publisher_name="Kaveri Bank Ltd",
            display_name="Kaveri Bank",
            canonical_url="https://apps.apple.com/in/app/kaveri-bank/id1234567890",
            icon_url="https://example.com/official_icon.png",
            relationship=Relationship.OFFICIAL,
            verification_method=VerificationMethod.STORE_LOOKUP,
            is_verified=True,
            trust_publisher=True,
        ),
    )
    asset_id = a_resp.id

    # 3. Create scan
    start_resp = store.create_scan(
        brand_id=brand_id,
        mode=ScanMode.LIVE,
        options=ScanOptions(
            asset_types=[AssetType.IOS_APP],
            source_ids=["apple_itunes"],
        ),
    )
    scan_id = start_resp.id

    # 4. Create findings
    finding_1_id = uuid4()
    finding_1 = FindingListItem(
        id=finding_1_id,
        brand_id=brand_id,
        scan_id=scan_id,
        candidate=CandidateSummary(
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="9876543210",
            display_name="Kaveri Bank Rewards",
            publisher_name="KB Rewards Studio",
            canonical_url="https://apps.apple.com/app/id9876543210",
        ),
        risk_score=75,
        severity=Severity.HIGH,
        evidence_coverage=1.0,
        technique=LookalikeTechnique.ADDED_WORD,
        top_signals=[
            TopSignal(
                signal="name_lookalike",
                points=19.5,
                max_points=25.0,
                reason="Added word 'Rewards' to brand name",
            )
        ],
        status=FindingStatus.NEW,
        source_mode=SourceMode.LIVE,
        observed_at=now,
    )

    finding_2_id = uuid4()
    finding_2 = FindingListItem(
        id=finding_2_id,
        brand_id=brand_id,
        scan_id=scan_id,
        candidate=CandidateSummary(
            platform="bluesky",
            asset_type=AssetType.SOCIAL_ACCOUNT,
            stable_identifier="did:plc:fakekaveri",
            display_name="Kaveri Official Support",
            handle="kaverisupport.bsky.social",
        ),
        risk_score=45,
        severity=Severity.MEDIUM,
        evidence_coverage=0.8,
        technique=LookalikeTechnique.ADDED_WORD,
        top_signals=[
            TopSignal(
                signal="name_lookalike",
                points=15.0,
                max_points=25.0,
                reason="Added word 'Support'",
            )
        ],
        status=FindingStatus.IN_REVIEW,
        source_mode=SourceMode.LIVE,
        observed_at=now,
    )

    # 5. Create cleared item
    cleared_1_id = uuid4()
    cleared_1 = ClearedListItem(
        id=cleared_1_id,
        scan_id=scan_id,
        candidate=ClearedCandidateSummary(
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="1234567890",
            display_name="Kaveri Bank",
            publisher_name="Kaveri Bank Ltd",
        ),
        decision=IdentityDecision.OFFICIAL_EXACT_MATCH,
        rule="R1_EXACT_ID",
        matched_official_asset_id=asset_id,
        explanation="Cleared: exact identifier match with registered official asset.",
        risk_score=None,
        source_mode=SourceMode.LIVE,
        observed_at=now,
    )

    # Save scan results
    store.save_scan_results(
        scan_id=scan_id,
        status=ScanStatus.COMPLETED,
        outcomes=[
            SourceOutcome(
                source_id="apple_itunes",
                status=SourceStatus.CONNECTED,
                source_mode=SourceMode.LIVE,
                queries_planned=1,
                queries_executed=1,
                candidate_count=3,
                cache_hit_count=0,
                retrieved_at=now,
                duration_ms=120,
            )
        ],
        funnel=ScanFunnel(
            retrieved=3,
            deduplicated=3,
            official_cleared=1,
            not_relevant=0,
            benign_lookalike=0,
            below_threshold=0,
            findings=2,
        ),
        findings_by_severity={"LOW": 0, "MEDIUM": 1, "HIGH": 1, "CRITICAL": 0},
        findings=[finding_1, finding_2],
        cleared=[cleared_1],
    )

    return {
        "brand_id": brand_id,
        "asset_id": asset_id,
        "scan_id": scan_id,
        "finding_1_id": finding_1_id,
        "finding_2_id": finding_2_id,
        "cleared_1_id": cleared_1_id,
    }


# ============================================================================
# 1. Sources Status Tests (Section 11.1)
# ============================================================================


def test_sources_status_fixed_list_and_unconnected(client: TestClient) -> None:
    """GET /api/v1/sources/status returns 9 source IDs with expected statuses."""
    res = client.get("/api/v1/sources/status")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 9

    by_id = {s["source_id"]: s for s in data}

    # Contract required fixed IDs
    expected_ids = [
        "apple_itunes",
        "bluesky_public",
        "bluesky_posts",
        "google_play_snapshot",
        "instagram",
        "x",
        "facebook",
        "demo_fixtures",
        "recorded_fixtures",
    ]
    for sid in expected_ids:
        assert sid in by_id, f"Source ID '{sid}' missing from status response!"

    # Explicitly NOT_CONNECTED per Section 11.1
    for unconnected in ["google_play_snapshot", "instagram", "x", "facebook"]:
        entry = by_id[unconnected]
        assert entry["status"] == "NOT_CONNECTED", (
            f"Expected {unconnected} to be explicitly NOT_CONNECTED, got {entry['status']}"
        )

    # Check apple_itunes fields
    apple = by_id["apple_itunes"]
    assert apple["status"] == "CONNECTED"
    assert "IOS_APP" in apple["asset_types"]
    assert "LIVE" in apple["supported_modes"]
    assert apple["default_mode"] == "LIVE"
    assert "About 20 requests per minute" in (apple["rate_limit_note"] or "")

    # Check bluesky_public fields
    bsky = by_id["bluesky_public"]
    assert bsky["status"] == "CONNECTED"
    assert "SOCIAL_ACCOUNT" in bsky["asset_types"]


class DummyAdapter(SourceAdapter):
    source_id = "apple_itunes"

    async def health_check(self) -> SourceHealth:
        return SourceHealth(
            source_id="apple_itunes",
            display_name="Apple App Store search",
            platform="apple_app_store",
            status=SourceStatus.CONNECTED,
            supported_modes=[SourceMode.LIVE],
            default_mode=SourceMode.LIVE,
            last_checked_at=datetime.now(timezone.utc),
            message="Health probe OK",
        )

    async def search(self, plan, limit, *, force_refresh, allow_stale_cache):
        return None  # pragma: no cover

    async def lookup(self, identifier: str):
        return None  # pragma: no cover


def test_sources_status_refresh(client: TestClient) -> None:
    """GET /api/v1/sources/status?refresh=true polls registered adapters."""
    register_source_adapter("apple_itunes", DummyAdapter())

    res = client.get("/api/v1/sources/status?refresh=true")
    assert res.status_code == 200
    data = res.json()
    apple = next(s for s in data if s["source_id"] == "apple_itunes")
    assert apple["status"] == "CONNECTED"
    assert "Health probe OK" in apple["message"]


# ============================================================================
# 2. Findings Listing & Filtering Tests (Section 11.5)
# ============================================================================


def test_list_findings_filters(client: TestClient) -> None:
    """GET /api/v1/findings supports documented query filters."""
    store = get_memory_store()
    seeded = seed_brand_with_assets_and_findings(store)
    b_id = seeded["brand_id"]
    s_id = seeded["scan_id"]

    # 1. Filter by brand_id
    res = client.get(f"/api/v1/findings?brand_id={b_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # 2. Filter by scan_id
    res = client.get(f"/api/v1/findings?scan_id={s_id}")
    assert res.status_code == 200
    assert res.json()["total"] == 2

    # 3. Filter by severity
    res = client.get(f"/api/v1/findings?brand_id={b_id}&severity=HIGH")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["severity"] == "HIGH"

    # 4. Filter by status
    res = client.get(f"/api/v1/findings?brand_id={b_id}&status=IN_REVIEW")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["candidate"]["display_name"] == "Kaveri Official Support"

    # 5. Filter by platform
    res = client.get(f"/api/v1/findings?brand_id={b_id}&platform=apple_app_store")
    assert res.status_code == 200
    assert res.json()["total"] == 1

    # 6. Filter by min_score
    res = client.get(f"/api/v1/findings?brand_id={b_id}&min_score=70")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["risk_score"] == 75

    # 7. Filter by text query q
    res = client.get(f"/api/v1/findings?brand_id={b_id}&q=rewards")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert "Rewards" in res.json()["items"][0]["candidate"]["display_name"]


def test_list_findings_latest_only(client: TestClient) -> None:
    """latest_only=True returns the newest assessment per candidate."""
    store = get_memory_store()
    seeded = seed_brand_with_assets_and_findings(store)
    b_id = seeded["brand_id"]
    s_id = seeded["scan_id"]

    # Add a newer assessment for the same candidate (apple_app_store, 9876543210)
    from datetime import timedelta
    newer_now = datetime.now(timezone.utc) + timedelta(minutes=5)
    newer_id = uuid4()
    newer_finding = FindingDetailResponse(
        id=newer_id,
        brand_id=b_id,
        scan_id=s_id,
        candidate=FindingDetailCandidate(
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="9876543210",
            display_name="Kaveri Bank Rewards v2",
        ),
        identity_guard=IdentityGuardResult(
            decision=IdentityDecision.CANDIDATE_FOR_REVIEW,
            rule="NO_EXACT_MATCH",
            explanation="Unregistered app",
        ),
        risk_score=85,
        severity=Severity.HIGH,
        evidence_coverage=1.0,
        technique=LookalikeTechnique.ADDED_WORD,
        source_mode=SourceMode.LIVE,
        status=FindingStatus.NEW,
        created_at=newer_now,
        observed_at=newer_now,
    )
    store.save_finding(newer_finding)

    # With latest_only=True (default): should return only 1 for 9876543210 (the newer one)
    res_latest = client.get(f"/api/v1/findings?brand_id={b_id}&platform=apple_app_store&latest_only=true")
    assert res_latest.status_code == 200
    items = res_latest.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(newer_id)
    assert items[0]["risk_score"] == 85

    # With latest_only=False: should return both assessments
    res_all = client.get(f"/api/v1/findings?brand_id={b_id}&platform=apple_app_store&latest_only=false")
    assert res_all.status_code == 200
    assert len(res_all.json()["items"]) == 2


def test_list_findings_include_dismissed(client: TestClient) -> None:
    """include_dismissed=False excludes dismissed findings unless explicitly requested."""
    store = get_memory_store()
    seeded = seed_brand_with_assets_and_findings(store)
    f1_id = seeded["finding_1_id"]

    # Mark finding 1 as dismissed
    client.patch(
        f"/api/v1/findings/{f1_id}",
        json={
            "status": "DISMISSED_FALSE_POSITIVE",
            "decision_reason": "Verified benign namesake",
        },
    )

    # By default, include_dismissed is False -> dismissed finding hidden
    r_default = client.get("/api/v1/findings")
    assert r_default.status_code == 200
    items = r_default.json()["items"]
    assert not any(i["id"] == str(f1_id) for i in items)

    # With include_dismissed=True -> dismissed finding included
    r_inc = client.get("/api/v1/findings?include_dismissed=true")
    assert r_inc.status_code == 200
    assert any(i["id"] == str(f1_id) for i in r_inc.json()["items"])

    # Explicit query for status=DISMISSED_FALSE_POSITIVE -> returned
    r_explicit = client.get("/api/v1/findings?status=DISMISSED_FALSE_POSITIVE")
    assert r_explicit.status_code == 200
    assert any(i["id"] == str(f1_id) for i in r_explicit.json()["items"])


def test_list_findings_sorting_and_pagination(client: TestClient) -> None:
    """GET /api/v1/findings supports sort ordering and pagination."""
    store = get_memory_store()
    seed_brand_with_assets_and_findings(store)

    # 1. sort=score_desc
    r_desc = client.get("/api/v1/findings?sort=score_desc")
    assert r_desc.status_code == 200
    items = r_desc.json()["items"]
    assert items[0]["risk_score"] >= items[1]["risk_score"]

    # 2. sort=score_asc
    r_asc = client.get("/api/v1/findings?sort=score_asc")
    assert r_asc.status_code == 200
    items_asc = r_asc.json()["items"]
    assert items_asc[0]["risk_score"] <= items_asc[1]["risk_score"]

    # 3. sort=name_asc
    r_name = client.get("/api/v1/findings?sort=name_asc")
    assert r_name.status_code == 200
    names = [i["candidate"]["display_name"] for i in r_name.json()["items"]]
    assert names == sorted(names)

    # 4. Pagination: limit=1, offset=0 and offset=1
    p1 = client.get("/api/v1/findings?limit=1&offset=0").json()
    assert p1["total"] == 2
    assert len(p1["items"]) == 1
    assert p1["limit"] == 1
    assert p1["offset"] == 0

    p2 = client.get("/api/v1/findings?limit=1&offset=1").json()
    assert len(p2["items"]) == 1
    assert p2["offset"] == 1
    assert p1["items"][0]["id"] != p2["items"][0]["id"]


# ============================================================================
# 3. Finding Detail Tests (Section 11.5)
# ============================================================================


def test_get_finding_detail(client: TestClient) -> None:
    """GET /api/v1/findings/{id} returns comprehensive breakdown, evidence, and limitations."""
    store = get_memory_store()
    seeded = seed_brand_with_assets_and_findings(store)
    f1_id = seeded["finding_1_id"]

    res = client.get(f"/api/v1/findings/{f1_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["id"] == str(f1_id)
    assert data["risk_score"] == 75
    assert data["severity"] == "HIGH"
    assert "candidate" in data
    assert data["candidate"]["display_name"] == "Kaveri Bank Rewards"
    assert "identity_guard" in data
    assert data["identity_guard"]["decision"] == "CANDIDATE_FOR_REVIEW"
    assert "score_breakdown" in data
    assert "evidence" in data
    assert "limitations" in data
    assert len(data["limitations"]) > 0
    assert data["scoring_version"] == "3.0.0"
    assert data["status"] == "NEW"
    assert data["decision_history"] == []


def test_get_finding_not_found(client: TestClient) -> None:
    """Unknown finding_id returns 404 NOT_FOUND error envelope."""
    unknown_id = str(uuid4())
    res = client.get(f"/api/v1/findings/{unknown_id}")
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == ApiErrorCode.NOT_FOUND.value
    assert "X-Request-ID" in res.headers


# ============================================================================
# 4. Analyst Decision Tests (Section 11.5)
# ============================================================================


def test_patch_finding_decision_validation_requires_reason(client: TestClient) -> None:
    """PATCH /findings/{id} requires decision_reason for DISMISSED and CONFIRMED."""
    store = get_memory_store()
    seeded = seed_brand_with_assets_and_findings(store)
    f1_id = seeded["finding_1_id"]

    # 1. DISMISSED_FALSE_POSITIVE without reason -> 422
    r1 = client.patch(
        f"/api/v1/findings/{f1_id}",
        json={"status": "DISMISSED_FALSE_POSITIVE"},
    )
    assert r1.status_code == 422
    assert r1.json()["error"]["code"] == ApiErrorCode.VALIDATION_ERROR.value

    # 2. CONFIRMED_SUSPICIOUS with empty reason -> 422
    r2 = client.patch(
        f"/api/v1/findings/{f1_id}",
        json={"status": "CONFIRMED_SUSPICIOUS", "decision_reason": "   "},
    )
    assert r2.status_code == 422
    assert r2.json()["error"]["code"] == ApiErrorCode.VALIDATION_ERROR.value

    # 3. Invalid enum status -> 422
    r3 = client.patch(
        f"/api/v1/findings/{f1_id}",
        json={"status": "NOT_AN_ENUM"},
    )
    assert r3.status_code == 422


def test_patch_finding_decision_success_and_audit(client: TestClient) -> None:
    """PATCH /findings/{id} updates status, decision history, candidate memory, and records audit event."""
    store = get_memory_store()
    seeded = seed_brand_with_assets_and_findings(store)
    b_id = seeded["brand_id"]
    f1_id = seeded["finding_1_id"]

    res = client.patch(
        f"/api/v1/findings/{f1_id}",
        json={
            "status": "DISMISSED_FALSE_POSITIVE",
            "decision_reason": "Unrelated publisher and different category",
            "notes": "Reviewed by senior analyst",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "DISMISSED_FALSE_POSITIVE"
    assert len(data["decision_history"]) == 1
    hist = data["decision_history"][0]
    assert hist["previous_status"] == "NEW"
    assert hist["new_status"] == "DISMISSED_FALSE_POSITIVE"
    assert hist["decision_reason"] == "Unrelated publisher and different category"
    assert hist["notes"] == "Reviewed by senior analyst"

    # Verify audit event written
    audit_res = client.get(f"/api/v1/brands/{b_id}/audit")
    assert audit_res.status_code == 200
    audit_events = audit_res.json()["items"]
    decision_events = [e for e in audit_events if e["event_type"] == "FINDING_DECISION"]
    assert len(decision_events) >= 1
    assert decision_events[0]["details"]["new_status"] == "DISMISSED_FALSE_POSITIVE"


def test_patch_finding_decision_preserves_sequential_history(client: TestClient) -> None:
    """Sequential decisions append to history without overwriting."""
    store = get_memory_store()
    seeded = seed_brand_with_assets_and_findings(store)
    f1_id = seeded["finding_1_id"]

    # Step 1: Mark IN_REVIEW
    client.patch(
        f"/api/v1/findings/{f1_id}",
        json={"status": "IN_REVIEW", "decision_reason": "Under review"},
    )

    # Step 2: Mark CONFIRMED_SUSPICIOUS
    res = client.patch(
        f"/api/v1/findings/{f1_id}",
        json={
            "status": "CONFIRMED_SUSPICIOUS",
            "decision_reason": "Impersonating brand logo and keywords",
        },
    )
    assert res.status_code == 200
    history = res.json()["decision_history"]
    assert len(history) == 2
    assert history[0]["new_status"] == "IN_REVIEW"
    assert history[1]["new_status"] == "CONFIRMED_SUSPICIOUS"


# ============================================================================
# 5. Finding Comparison Tests (Section 11.5)
# ============================================================================


def test_finding_comparison_resolves_and_calls_compare(client: TestClient) -> None:
    """GET /findings/{id}/comparison resolves nearest official asset and delegates to compare()."""
    store = get_memory_store()
    seeded = seed_brand_with_assets_and_findings(store)
    f1_id = seeded["finding_1_id"]

    # Call with mock Person 4 compare function
    mock_field_comparison = [
        FieldComparison(
            field="display_name",
            official_value="Kaveri Bank",
            candidate_value="Kaveri Bank Rewards",
            similarity=0.85,
            name_diff=[
                NameDiffSegment(text="Kaveri Bank", changed=False),
                NameDiffSegment(text=" Rewards", changed=True),
            ],
            non_ascii_chars=[
                NonAsciiChar(char="★", codepoint="U+2605", index=0)
            ],
        ),
        FieldComparison(
            field="publisher_name",
            official_value="Kaveri Bank Ltd",
            candidate_value="KB Rewards Studio",
            similarity=0.31,
        ),
    ]

    with patch("app.api.routes.findings.compare", return_value=mock_field_comparison) as mock_compare:
        res = client.get(f"/api/v1/findings/{f1_id}/comparison")
        assert res.status_code == 200
        data = res.json()

        # Check compare() interface was called with correct types
        assert mock_compare.called
        args, _ = mock_compare.call_args
        cand_arg, official_arg = args
        assert isinstance(cand_arg, NormalizedCandidate)
        assert isinstance(official_arg, OfficialAssetCtx)
        assert cand_arg.display_name == "Kaveri Bank Rewards"
        assert official_arg.display_name == "Kaveri Bank"

        # Check returned payload
        assert data["finding_id"] == str(f1_id)
        assert data["official_asset"]["display_name"] == "Kaveri Bank"
        assert data["candidate_asset"]["display_name"] == "Kaveri Bank Rewards"
        assert len(data["comparisons"]) == 2
        name_cmp = data["comparisons"][0]
        assert name_cmp["field"] == "display_name"
        assert name_cmp["similarity"] == 0.85
        assert name_cmp["name_diff"][1]["changed"] is True
        assert name_cmp["non_ascii_chars"][0]["codepoint"] == "U+2605"
        assert "Similarity indicates a candidate for review" in data["disclaimer"]


def test_finding_comparison_not_found(client: TestClient) -> None:
    """Unknown finding_id returns 404 NOT_FOUND."""
    unknown_id = str(uuid4())
    res = client.get(f"/api/v1/findings/{unknown_id}/comparison")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == ApiErrorCode.NOT_FOUND.value


# ============================================================================
# 6. Cleared Items Tests (Section 11.5)
# ============================================================================


def test_brand_cleared_listing_and_filters(client: TestClient) -> None:
    """GET /api/v1/brands/{brand_id}/cleared lists cleared items with filters."""
    store = get_memory_store()
    seeded = seed_brand_with_assets_and_findings(store)
    b_id = seeded["brand_id"]
    s_id = seeded["scan_id"]

    # 1. List all cleared for brand
    res = client.get(f"/api/v1/brands/{b_id}/cleared")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["decision"] == "OFFICIAL_EXACT_MATCH"
    assert data["items"][0]["rule"] == "R1_EXACT_ID"

    # 2. Filter by decision
    r_dec = client.get(f"/api/v1/brands/{b_id}/cleared?decision=OFFICIAL_EXACT_MATCH")
    assert r_dec.status_code == 200
    assert r_dec.json()["total"] == 1

    r_none = client.get(f"/api/v1/brands/{b_id}/cleared?decision=BENIGN_LOOKALIKE")
    assert r_none.status_code == 200
    assert r_none.json()["total"] == 0

    # 3. Filter by scan_id
    r_scan = client.get(f"/api/v1/brands/{b_id}/cleared?scan_id={s_id}")
    assert r_scan.status_code == 200
    assert r_scan.json()["total"] == 1

    # 4. Unknown brand returns 404
    bad_id = str(uuid4())
    r_bad = client.get(f"/api/v1/brands/{bad_id}/cleared")
    assert r_bad.status_code == 404
    assert r_bad.json()["error"]["code"] == ApiErrorCode.NOT_FOUND.value


# ============================================================================
# 7. Audit Trail Tests (Section 11.5)
# ============================================================================


def test_brand_audit_trail_and_pagination(client: TestClient) -> None:
    """GET /api/v1/brands/{brand_id}/audit lists audit events newest first with pagination."""
    store = get_memory_store()
    seeded = seed_brand_with_assets_and_findings(store)
    b_id = seeded["brand_id"]
    a_id = seeded["asset_id"]

    # Trigger asset update audit event
    client.patch(
        f"/api/v1/brands/{b_id}/assets/{a_id}",
        json={"notes": "Updated verification note"},
    )

    res = client.get(f"/api/v1/brands/{b_id}/audit?limit=10&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    items = data["items"]
    assert items[0]["brand_id"] == str(b_id)
    assert items[0]["actor_label"] == "analyst"
    assert items[0]["event_type"] == "ASSET_UPDATED"

    # Unknown brand -> 404
    bad_id = str(uuid4())
    r_bad = client.get(f"/api/v1/brands/{bad_id}/audit")
    assert r_bad.status_code == 404
    assert r_bad.json()["error"]["code"] == ApiErrorCode.NOT_FOUND.value


# ============================================================================
# 8. Brand Summary Aggregation Tests (Section 11.2)
# ============================================================================


def test_brand_summary_aggregates_computed_from_stored_data(client: TestClient) -> None:
    """GET /api/v1/brands/{brand_id}/summary computes exact aggregates from stored data."""
    store = get_memory_store()
    seeded = seed_brand_with_assets_and_findings(store)
    b_id = seeded["brand_id"]
    f1_id = seeded["finding_1_id"]

    # Initially: 1 NEW, 1 IN_REVIEW -> reviewed: 1, total: 2
    res = client.get(f"/api/v1/brands/{b_id}/summary")
    assert res.status_code == 200
    summary = res.json()

    assert summary["brand_id"] == str(b_id)
    assert summary["official_asset_count"] == 1
    assert summary["last_scan"] is not None
    assert summary["last_scan"]["status"] == "COMPLETED"
    assert summary["funnel"]["retrieved"] == 3
    assert summary["funnel"]["deduplicated"] == 3
    assert summary["funnel"]["official_cleared"] == 1
    assert summary["funnel"]["findings"] == 2

    assert summary["findings_by_severity"] == {"LOW": 0, "MEDIUM": 1, "HIGH": 1, "CRITICAL": 0}
    assert summary["findings_by_status"]["NEW"] == 1
    assert summary["findings_by_status"]["IN_REVIEW"] == 1
    assert summary["findings_by_platform"]["apple_app_store"] == 1
    assert summary["findings_by_platform"]["bluesky"] == 1

    assert summary["cleared_by_decision"]["OFFICIAL_EXACT_MATCH"] == 1
    assert summary["review_progress"] == {"reviewed": 1, "total": 2}
    assert len(summary["source_coverage"]) == 1
    assert summary["source_coverage"][0]["source_id"] == "apple_itunes"

    # Now make an analyst decision on finding 1 -> reviewed should increase to 2
    client.patch(
        f"/api/v1/findings/{f1_id}",
        json={
            "status": "CONFIRMED_SUSPICIOUS",
            "decision_reason": "Confirmed impersonation",
        },
    )

    res2 = client.get(f"/api/v1/brands/{b_id}/summary")
    assert res2.status_code == 200
    summary2 = res2.json()
    assert summary2["findings_by_status"]["NEW"] == 0
    assert summary2["findings_by_status"]["CONFIRMED_SUSPICIOUS"] == 1
    assert summary2["review_progress"] == {"reviewed": 2, "total": 2}


def test_brand_summary_not_found(client: TestClient) -> None:
    """Unknown brand_id returns 404 NOT_FOUND."""
    unknown_id = str(uuid4())
    res = client.get(f"/api/v1/brands/{unknown_id}/summary")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == ApiErrorCode.NOT_FOUND.value
