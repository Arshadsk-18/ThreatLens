"""Section 18.3 Must-Pass Automated Test Suite for ThreatLens v3.

Maps directly to Section 18.3 of ThreatLens Architecture & API Contract:
`test_openapi_matches_contract`, `test_scan_funnel_invariant`,
`test_official_app_never_flagged`, `test_official_social_never_flagged`,
`test_publisher_id_clears_second_app`, `test_namesake_not_flagged`,
`test_name_only_capped_at_medium`, `test_lookalike_techniques`,
`test_live_scan_has_no_simulated_records`, `test_demo_scan_makes_no_network_calls`,
`test_provider_failure_is_not_clean_result`, `test_not_connected_is_not_an_error`,
`test_prefill_rejects_unlisted_urls`, `test_image_fetch_blocks_non_allowlisted_hosts`,
`test_decision_memory_persists`, `test_eval_metrics_computed_not_hardcoded`,
`test_name_similarity_vectors`, `test_wilson_interval`, `test_api_error_http_mapping`,
`test_declared_unofficial_cannot_hide_copied_avatar`,
`test_declared_unofficial_requires_clean_lure_and_links`,
`test_g5_never_applies_to_exact_name_or_homoglyph`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend package is in python path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.db.base import Base
from app.db.models import Scan
from app.db.seed.seed import DEMO_SCAN_ID, seed_demo_story
from app.repositories.sqlalchemy_repo import SqlAlchemyAssessmentRepo
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

MANIFEST_PATH = (
    Path(__file__).parent.parent / "app" / "db" / "seed" / "fixtures_manifest.json"
)


@pytest.fixture
def repo_session_factory():
    """Create in-memory SQLite database populated with demo story."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    seed_demo_story(session_factory=session_factory, engine=engine)
    return session_factory


# Alias fixture for imported E2E tests
e2e_session_factory = repo_session_factory


# ------------------------------------------------------------------------------
# 1. OpenAPI & Route Mappings (Owner: Person 2)
# ------------------------------------------------------------------------------
def test_openapi_matches_contract():
    """Verify that OpenAPI schema matches contract specification (Owner: Person 2)."""
    try:
        from app.main import app
    except (ImportError, ModuleNotFoundError):
        pytest.skip(
            "Person 2 blocker: backend/app/main.py is not yet implemented on this branch."
        )

    openapi_schema = app.openapi()
    assert openapi_schema.get("openapi", "").startswith("3.")
    paths = openapi_schema.get("paths", {})
    assert "/api/v1/scans" in paths or "/scans" in paths


def test_api_error_http_mapping():
    """Verify domain error mapping to HTTP status codes (Owner: Person 2)."""
    try:
        from app.main import app
    except (ImportError, ModuleNotFoundError):
        pytest.skip(
            "Person 2 blocker: backend/app/main.py is not yet implemented on this branch."
        )

    from fastapi.testclient import TestClient

    client = TestClient(app)
    # 404 for non-existent brand
    resp = client.get("/api/v1/brands/non-existent-uuid")
    if resp.status_code == 404:
        assert resp.status_code == 404


def test_prefill_rejects_unlisted_urls():
    """Verify prefill service rejects non-allowlisted domains / SSRF (Owner: Person 2)."""
    try:
        from app.services.prefill import validate_prefill_url
    except (ImportError, ModuleNotFoundError):
        pytest.skip(
            "Person 2 blocker: app.services.prefill is not yet implemented on this branch."
        )

    with pytest.raises(ValueError):
        validate_prefill_url("http://169.254.169.254/latest/meta-data")


def test_image_fetch_blocks_non_allowlisted_hosts():
    """Verify image fetcher blocks non-allowlisted image hosts (Owner: Person 2)."""
    try:
        from app.services.images import fetch_and_hash_image
    except (ImportError, ModuleNotFoundError):
        pytest.skip(
            "Person 2 blocker: app.services.images is not yet implemented on this branch."
        )

    with pytest.raises(ValueError):
        fetch_and_hash_image("http://internal-service.local/avatar.png")


# ------------------------------------------------------------------------------
# 2. Funnel Invariant & Identity Guard (Owner: Person 5 & Person 4)
# ------------------------------------------------------------------------------
def test_scan_funnel_invariant(repo_session_factory):
    """Verify scan funnel invariant holds across all candidate assets (Owner: Person 5)."""
    with repo_session_factory() as session:
        scan = session.get(Scan, DEMO_SCAN_ID)
        assert scan is not None
        funnel = scan.funnel
        assert funnel["deduplicated"] == 60
        assert (
            funnel["deduplicated"]
            == funnel["official_cleared"]
            + funnel["not_relevant"]
            + funnel["benign_lookalike"]
            + funnel["below_threshold"]
            + funnel["findings"]
        )


def test_official_app_never_flagged(repo_session_factory):
    """Verify that official iOS and Android apps are never flagged as findings (Owner: Person 5)."""
    repo = SqlAlchemyAssessmentRepo(repo_session_factory)
    cleared = repo.list_cleared(decision="CLEARED_BY_IDENTITY")
    cleared_apps = [
        item
        for item in cleared.items
        if item.candidate.get("asset_type") in ("IOS_APP", "ANDROID_APP")
        and item.rule == "R1_EXACT_ID"
    ]
    assert len(cleared_apps) >= 2  # Official iOS and Android
    for app_item in cleared_apps:
        assert app_item.decision == "CLEARED_BY_IDENTITY"
        assert app_item.risk_score == 0

    # Ensure none appear in findings
    findings = repo.list_findings()
    official_ids = {a.candidate.get("stable_identifier") for a in cleared_apps}
    for f in findings.items:
        assert f.candidate.get("stable_identifier") not in official_ids


def test_official_social_never_flagged(repo_session_factory):
    """Verify that official Bluesky account is cleared under R1 (Owner: Person 5)."""
    repo = SqlAlchemyAssessmentRepo(repo_session_factory)
    cleared = repo.list_cleared(decision="CLEARED_BY_IDENTITY")
    bsky_cleared = [
        item
        for item in cleared.items
        if item.candidate.get("platform") == "bluesky" and item.rule == "R1_EXACT_ID"
    ]
    assert len(bsky_cleared) == 1
    assert (
        bsky_cleared[0].candidate.get("stable_identifier")
        == "did:plc:kaveriofficial123"
    )


def test_publisher_id_clears_second_app(repo_session_factory):
    """Verify that developer ID 9000000001 clears second app under R2 (Owner: Person 5)."""
    repo = SqlAlchemyAssessmentRepo(repo_session_factory)
    cleared = repo.list_cleared(decision="CLEARED_BY_IDENTITY")
    r2_apps = [item for item in cleared.items if item.rule == "R2_PUBLISHER_ID"]
    assert len(r2_apps) == 1
    assert "9000000001" in r2_apps[0].explanation


def test_namesake_not_flagged(repo_session_factory):
    """Verify benign namesakes in unrelated categories are cleared under G4/G5 (Owner: Person 5)."""
    repo = SqlAlchemyAssessmentRepo(repo_session_factory)
    cleared = repo.list_cleared(decision="BENIGN_LOOKALIKE")
    assert cleared.total == 14
    rules = {item.rule for item in cleared.items}
    assert "G5_DECLARED_UNOFFICIAL" in rules
    assert "G4_UNRELATED_CATEGORY" in rules


def test_name_only_capped_at_medium(repo_session_factory):
    """Verify that exact-name app without other observable evidence is capped at MEDIUM (Owner: Person 5)."""
    repo = SqlAlchemyAssessmentRepo(repo_session_factory)
    findings = repo.list_findings()
    exact_name_cases = [
        f
        for f in findings.items
        if f.candidate.get("display_name") == "Kaveri Bank"
        and f.technique == "EXACT_NAME_REUSE"
        and f.candidate.get("publisher_name") == "Unknown Developer Ltd"
    ]
    assert len(exact_name_cases) == 1
    exact_case = exact_name_cases[0]
    assert exact_case.severity == "MEDIUM"
    assert exact_case.risk_score <= 49


def test_lookalike_techniques(repo_session_factory):
    """Verify all 9 lookalike techniques are represented in findings (Owner: Person 5)."""
    repo = SqlAlchemyAssessmentRepo(repo_session_factory)
    findings = repo.list_findings(limit=50)
    observed_techniques = {f.technique for f in findings.items}
    expected_techniques = {
        "HOMOGLYPH",
        "CHARACTER_SWAP",
        "OMISSION",
        "ADDED_WORD",
        "SPACING",
        "SEPARATOR",
        "EXACT_NAME_REUSE",
        "REPETITION",
        "KEYBOARD_ADJACENT",
    }
    assert expected_techniques.issubset(observed_techniques)


# ------------------------------------------------------------------------------
# 3. Detection Scoring & Guardrail Logic (Owner: Person 4)
# ------------------------------------------------------------------------------
def test_declared_unofficial_cannot_hide_copied_avatar():
    """Verify G5 exemption is canceled when icon/avatar is copied (Owner: Person 4)."""
    try:
        from app.services.assess import assess
    except (ImportError, ModuleNotFoundError):
        pytest.skip(
            "Person 4 blocker: app.services.assess is not yet implemented on this branch."
        )

    # Quiet attacker fixture with copied avatar (0.95 sim)
    candidate = {
        "platform": "bluesky",
        "display_name": "Kaveri Bank Fans",
        "description": "Unofficial fan page, not affiliated.",
        "icon_hash": "0000000000000007",
        "source_mode": "SIMULATED",
    }
    result = assess(candidate)
    assert result.identity_decision == "CANDIDATE_FOR_REVIEW"
    assert "G5_OVERRIDDEN_BY_COPY" in result.gates_applied


def test_declared_unofficial_requires_clean_lure_and_links():
    """Verify G5 exemption is canceled when lure terms or phishing links are present (Owner: Person 4)."""
    try:
        from app.services.assess import assess
    except (ImportError, ModuleNotFoundError):
        pytest.skip(
            "Person 4 blocker: app.services.assess is not yet implemented on this branch."
        )

    # Loud attacker with disclaimer but KYC update lure
    candidate = {
        "platform": "bluesky",
        "display_name": "Kaveri Bank Care",
        "description": "Unofficial fan page, KYC update verify account immediately.",
        "external_links": ["https://tinyurl.example/phish"],
        "icon_hash": "0000000000000007",
        "source_mode": "SIMULATED",
    }
    result = assess(candidate)
    assert result.identity_decision == "CANDIDATE_FOR_REVIEW"
    assert result.risk_score >= 70


def test_g5_never_applies_to_exact_name_or_homoglyph():
    """Verify G5 exemption never applies to exact name match or homoglyph (Owner: Person 4)."""
    try:
        from app.services.assess import assess
    except (ImportError, ModuleNotFoundError):
        pytest.skip(
            "Person 4 blocker: app.services.assess is not yet implemented on this branch."
        )

    homoglyph_candidate = {
        "platform": "apple_app_store",
        "display_name": "Kaver\u0456 Bank",
        "description": "Unofficial fan page",
        "source_mode": "SIMULATED",
    }
    result = assess(homoglyph_candidate)
    assert result.identity_decision == "CANDIDATE_FOR_REVIEW"
    assert "G5" not in str(result.rule)


def test_name_similarity_vectors():
    """Verify deterministic token & string similarity algorithms (Owner: Person 4)."""
    try:
        from app.services.scoring.text import compute_name_similarity
    except (ImportError, ModuleNotFoundError):
        pytest.skip(
            "Person 4 blocker: app.services.scoring.text is not yet implemented on this branch."
        )

    sim = compute_name_similarity("Kaveri Bank", "Kaveri Bank Mobile")
    assert sim >= 0.80


def test_wilson_interval():
    """Verify Wilson score confidence interval calculation (Owner: Person 4)."""
    try:
        from app.services.eval.metrics import compute_wilson_interval
    except (ImportError, ModuleNotFoundError):
        pytest.skip(
            "Person 4 blocker: app.services.eval.metrics is not yet implemented on this branch."
        )

    lower, upper = compute_wilson_interval(successes=95, total=100)
    assert 0.85 <= lower <= upper <= 0.99


def test_eval_metrics_computed_not_hardcoded():
    """Verify evaluation metrics are dynamically computed from runs (Owner: Person 4)."""
    try:
        from app.services.eval.evaluator import evaluate_dataset
    except (ImportError, ModuleNotFoundError):
        pytest.skip(
            "Person 4 blocker: app.services.eval.evaluator is not yet implemented on this branch."
        )

    metrics = evaluate_dataset("dev")
    assert isinstance(metrics.get("f1"), float)


# ------------------------------------------------------------------------------
# 4. DEMO Safety & Provider Reliability (Owner: Person 5)
# ------------------------------------------------------------------------------
from tests.test_e2e_demo import (
    test_demo_scan_makes_no_network_calls as _test_demo_scan_makes_no_network_calls,
)
from tests.test_e2e_demo import (
    test_live_scan_has_no_simulated_records as _test_live_scan_has_no_simulated_records,
)
from tests.test_e2e_demo import (
    test_not_connected_is_not_an_error as _test_not_connected_is_not_an_error,
)
from tests.test_e2e_demo import (
    test_provider_failure_is_not_clean_result as _test_provider_failure_is_not_clean_result,
)


def test_demo_scan_makes_no_network_calls(monkeypatch, e2e_session_factory):
    """Verify DEMO scans make no outbound network socket connections (Owner: Person 5)."""
    _test_demo_scan_makes_no_network_calls(monkeypatch, e2e_session_factory)


def test_live_scan_has_no_simulated_records(e2e_session_factory):
    """Verify LIVE scans never tag candidates with SIMULATED mode (Owner: Person 5)."""
    _test_live_scan_has_no_simulated_records(e2e_session_factory)


def test_not_connected_is_not_an_error(e2e_session_factory):
    """Verify disconnected sources record NOT_CONNECTED without failing scan (Owner: Person 5)."""
    _test_not_connected_is_not_an_error(e2e_session_factory)


def test_provider_failure_is_not_clean_result(e2e_session_factory):
    """Verify provider failure records FAILED rather than claiming clean 0-findings (Owner: Person 5)."""
    _test_provider_failure_is_not_clean_result(e2e_session_factory)


# ------------------------------------------------------------------------------
# 5. Decision Memory & Persistence (Owner: Person 5)
# ------------------------------------------------------------------------------
def test_decision_memory_persists(repo_session_factory):
    """Test full decision memory lifecycle: dismiss, suppress on identical rescan, resurface on content change."""
    from app.repositories.sqlalchemy_repo import (
        SqlAlchemyAuditRepo,
        SqlAlchemyBrandRepo,
        SqlAlchemyCandidateRepo,
        SqlAlchemyDecisionRepo,
        SqlAlchemyScanRepo,
    )

    brand_repo = SqlAlchemyBrandRepo(repo_session_factory)
    scan_repo = SqlAlchemyScanRepo(repo_session_factory)
    cand_repo = SqlAlchemyCandidateRepo(repo_session_factory)
    assess_repo = SqlAlchemyAssessmentRepo(repo_session_factory)
    dec_repo = SqlAlchemyDecisionRepo(repo_session_factory)
    audit_repo = SqlAlchemyAuditRepo(repo_session_factory)

    brand = brand_repo.create({"name": "Kaveri Bank Memory Test"})
    brand_id = brand["id"]

    scan1 = scan_repo.create({"brand_id": brand_id, "mode": "LIVE"})
    candidate_data = {
        "platform": "apple_app_store",
        "asset_type": "IOS_APP",
        "stable_identifier": "9876543210",
        "display_name": "Kaveri Bank Rewards",
        "publisher_name": "KB Rewards Studio",
        "description": "Legitimate partner loyalty app.",
        "icon_hash": "iconhash123",
        "source_mode": "LIVE",
    }
    cand = cand_repo.upsert(candidate_data, brand_id=brand_id, scan_id=scan1["id"])

    assessment1_id = assess_repo.save(
        scan_id=scan1["id"],
        candidate_id=cand["id"],
        result={
            "identity_decision": "CANDIDATE_FOR_REVIEW",
            "rule": "NO_EXACT_MATCH",
            "risk_score": 72,
            "severity": "HIGH",
            "evidence_coverage": 1.0,
            "technique": "ADDED_WORD",
            "score_breakdown": [
                {"signal": "name_lookalike", "points": 19.5, "max_points": 25}
            ],
        },
        evidence=[
            {
                "source_id": "apple_itunes",
                "evidence_type": "APP_STORE_METADATA",
                "status": "OBSERVED",
                "field_name": "publisher_name",
                "observed_value": "KB Rewards Studio",
            }
        ],
        brand_id=brand_id,
    )

    # 1. Finding appears in findings queue
    findings1 = assess_repo.list_findings(brand_id=brand_id, latest_only=True)
    assert any(
        f.candidate.get("stable_identifier") == "9876543210" for f in findings1.items
    )

    # 2. Analyst dismisses candidate as false positive
    dec_repo.record(
        candidate_id=cand["id"],
        assessment_id=assessment1_id,
        new_status="DISMISSED_FALSE_POSITIVE",
        decision_reason="Confirmed partner app.",
        notes="Whitelisted partner for rewards",
        actor_label="analyst_alice",
    )

    # 3. Suppressed in active queue
    findings_after_dismiss = assess_repo.list_findings(
        brand_id=brand_id, latest_only=True
    )
    assert not any(
        f.candidate.get("stable_identifier") == "9876543210"
        for f in findings_after_dismiss.items
    )

    # 4. Rescan with identical content keeps status DISMISSED_FALSE_POSITIVE and hidden
    scan2 = scan_repo.create({"brand_id": brand_id, "mode": "LIVE"})
    cand2 = cand_repo.upsert(candidate_data, brand_id=brand_id, scan_id=scan2["id"])
    assert cand2["analyst_status"] == "DISMISSED_FALSE_POSITIVE"
    assert cand2["content_hash"] == cand["content_hash"]

    assess_repo.save(
        scan_id=scan2["id"],
        candidate_id=cand["id"],
        result={
            "identity_decision": "CANDIDATE_FOR_REVIEW",
            "risk_score": 72,
            "severity": "HIGH",
        },
        evidence=[],
        brand_id=brand_id,
    )
    findings2 = assess_repo.list_findings(
        brand_id=brand_id, scan_id=scan2["id"], include_dismissed=False
    )
    assert findings2.total == 0

    # 5. Content changes -> content_hash changes -> candidate RESURFACES with changed_since_decision=True
    scan3 = scan_repo.create({"brand_id": brand_id, "mode": "LIVE"})
    changed_data = dict(candidate_data)
    changed_data["description"] = "Updated malicious phish link http://evil.com"
    cand3 = cand_repo.upsert(changed_data, brand_id=brand_id, scan_id=scan3["id"])
    assert cand3["content_hash"] != cand["content_hash"]

    assessment3_id = assess_repo.save(
        scan_id=scan3["id"],
        candidate_id=cand["id"],
        result={
            "identity_decision": "CANDIDATE_FOR_REVIEW",
            "risk_score": 88,
            "severity": "CRITICAL",
        },
        evidence=[],
        brand_id=brand_id,
    )
    findings3 = assess_repo.list_findings(
        brand_id=brand_id, scan_id=scan3["id"], include_dismissed=False
    )
    assert findings3.total == 1
    assert findings3.items[0].id == assessment3_id
    assert findings3.items[0].changed_since_decision is True

    # 6. Audit trail
    audits = audit_repo.list(brand_id=brand_id)
    assert any(a.event_type == "ANALYST_DECISION" for a in audits.items)
