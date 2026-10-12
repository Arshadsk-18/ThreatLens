"""QA test suite for ThreatLens Kaveri Bank demo story and fixtures manifest (Appendix B)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure backend package is in python path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.base import Base
from app.db.models import Assessment, Brand, CandidateAsset, OfficialAsset, Scan
from app.db.seed.seed import DEMO_SCAN_ID, seed_demo_story
from app.repositories.sqlalchemy_repo import SqlAlchemyAssessmentRepo
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

MANIFEST_PATH = (
    Path(__file__).parent.parent / "app" / "db" / "seed" / "fixtures_manifest.json"
)


def test_manifest_structure_and_composition():
    """Verify that fixtures_manifest.json matches Section 8.7 and Appendix B exactly."""
    assert MANIFEST_PATH.exists(), f"Manifest file missing at {MANIFEST_PATH}"

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        data = json.load(f)

    fixtures: list[dict[str, Any]] = data.get("fixtures", [])
    assert len(fixtures) == 60, f"Expected exactly 60 fixtures, got {len(fixtures)}"

    cleared = [f for f in fixtures if f["intended_label"].startswith("cleared_")]
    benign = [f for f in fixtures if f["intended_label"].startswith("benign_")]
    impersonation = [
        f for f in fixtures if f["intended_label"].startswith("impersonation_")
    ]
    not_relevant = [f for f in fixtures if f["intended_label"] == "not_relevant"]

    assert len(cleared) == 5, f"Expected 5 cleared, got {len(cleared)}"
    assert len(benign) == 14, f"Expected 14 benign, got {len(benign)}"
    assert len(impersonation) == 12, (
        f"Expected 12 impersonation, got {len(impersonation)}"
    )
    assert len(not_relevant) == 29, f"Expected 29 not_relevant, got {len(not_relevant)}"

    # Funnel invariant
    assert len(cleared) + len(benign) + len(impersonation) + len(not_relevant) == 60

    # Check that all 9 techniques are represented across the impersonation fixtures
    techniques_in_fixtures = {
        f["intended_label"].replace("impersonation_", "").upper() for f in impersonation
    }
    required_techniques = {
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
    assert required_techniques.issubset(techniques_in_fixtures), (
        f"Missing techniques: {required_techniques - techniques_in_fixtures}"
    )

    # Check platforms covered across impersonation
    platforms = {f["platform"] for f in impersonation}
    assert {
        "apple_app_store",
        "google_play",
        "bluesky",
        "x",
        "instagram",
        "facebook",
    }.issubset(platforms)

    # Check perceptual hash values match Section 8.7 math
    p_hashes = {
        f["id"]: f["candidate"].get("icon_hash")
        for f in fixtures
        if f["candidate"].get("icon_hash") is not None
    }
    # Copied icon (0.93 similarity, Hamming 4)
    assert p_hashes.get("c-0020") == "000000000000000f"
    # Copied avatar (0.95 similarity, Hamming 3)
    assert p_hashes.get("c-0026") == "0000000000000007"
    assert p_hashes.get("c-0027") == "0000000000000007"
    # Benign non-copies (0.55 similarity, Hamming 29)
    assert p_hashes.get("c-0006") == "000000001f7f7fff"
    assert p_hashes.get("c-0007") == "000000001f7f7fff"

    # Privacy check: No real brands or Indian public banks
    disallowed_brand_names = {
        "SBI",
        "HDFC",
        "ICICI",
        "Canara",
        "Axis",
        "PNB",
        "Federal",
    }
    for f in fixtures:
        display_name = f["candidate"].get("display_name", "")
        for forbidden in disallowed_brand_names:
            assert forbidden.lower() not in display_name.lower().split(), (
                f"Disallowed real brand word '{forbidden}' found in fixture {f['id']}: {display_name}"
            )


def test_seed_script_idempotent_on_empty_db():
    """Verify that seed_demo_story loads into an empty DB idempotently and respects invariants."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    # 1. First run on empty DB
    summary_1 = seed_demo_story(session_factory=session_factory, engine=engine)
    assert summary_1["total_seeded"] == 60
    assert summary_1["cleared_count"] == 5
    assert summary_1["lookalike_count"] == 14
    assert summary_1["findings_count"] == 12
    assert summary_1["not_relevant_count"] == 29

    with session_factory() as session:
        brand_count = session.query(Brand).count()
        asset_count = session.query(OfficialAsset).count()
        scan_count = session.query(Scan).count()
        cand_count = session.query(CandidateAsset).count()
        ass_count = session.query(Assessment).count()

        assert brand_count == 1
        assert asset_count == 4
        assert scan_count == 1
        assert cand_count == 60
        assert ass_count == 60

        scan = session.query(Scan).filter_by(id=DEMO_SCAN_ID).one()
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

    # 2. Second run on existing DB (idempotence verification)
    summary_2 = seed_demo_story(session_factory=session_factory, engine=engine)
    assert summary_2 == summary_1

    with session_factory() as session:
        assert session.query(Brand).count() == 1
        assert session.query(OfficialAsset).count() == 4
        assert session.query(Scan).count() == 1
        assert session.query(CandidateAsset).count() == 60
        assert session.query(Assessment).count() == 60


def test_cleared_query_returns_rule_and_explanation():
    """Verify that list_cleared returns rule, matched_official_asset_id, explanation, and supports search."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    seed_demo_story(session_factory=session_factory, engine=engine)
    repo = SqlAlchemyAssessmentRepo(session_factory)

    # All non-findings (5 identity cleared + 14 benign + 29 not relevant = 48)
    cleared_page = repo.list_cleared(limit=100)
    assert cleared_page.total == 48

    for item in cleared_page.items:
        assert item.rule, f"Rule missing on cleared record {item.id}"
        assert item.explanation, f"Explanation missing on cleared record {item.id}"
        assert item.decision in {
            "CLEARED_BY_IDENTITY",
            "BENIGN_LOOKALIKE",
            "BELOW_THRESHOLD",
        }

    # Identity cleared specifically
    identity_page = repo.list_cleared(decision="CLEARED_BY_IDENTITY")
    assert identity_page.total == 5
    for item in identity_page.items:
        assert item.matched_official_asset_id is not None
        assert item.rule in {"R1_EXACT_ID", "R2_PUBLISHER_ID", "R3_PARTNER"}
        assert len(item.explanation) > 10

    # Search on display_name via q
    search_mobile = repo.list_cleared(q="Mobile")
    assert search_mobile.total >= 1
    assert any(
        "Mobile" in r.candidate.get("display_name", "") for r in search_mobile.items
    )

    search_coffee = repo.list_cleared(q="Coffee")
    assert search_coffee.total == 1
    assert "Kaveri Coffee Roasters" in search_coffee.items[0].candidate.get(
        "display_name", ""
    )


def test_demo_story_matches_manifest():
    """QA test: Run the real assess() from Person 4 over every fixture and assert story invariants.

    Per Rule 3:
    - Skip with a clear reason if assess() is not yet implemented or raises NotImplementedError.
    - If assess() is implemented: assert all 5 identity-cleared are cleared with the right rule;
      no official asset is ever a finding; every benign lookalike is BENIGN_LOOKALIKE or
      BELOW_THRESHOLD; each impersonation is CANDIDATE_FOR_REVIEW; exact-name-only is capped at MEDIUM;
      and funnel invariant holds.
    """
    try:
        from app.services.assess import assess  # type: ignore
    except (ImportError, ModuleNotFoundError):
        pytest.skip(
            "Person 4's app.services.assess is not yet merged/available on this branch. "
            "Skipping manifest scoring execution test."
        )

    # If assess is present, load fixtures and official assets
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        data = json.load(f)
    fixtures = data.get("fixtures", [])

    # Run assess against fixtures
    counts = {
        "official_cleared": 0,
        "not_relevant": 0,
        "benign_lookalike": 0,
        "below_threshold": 0,
        "findings": 0,
    }

    mismatches: list[str] = []

    for item in fixtures:
        f_id = item["id"]
        intended_label = item["intended_label"]
        cand = item["candidate"]

        try:
            res = assess(cand)
        except NotImplementedError:
            pytest.skip(
                "assess() raised NotImplementedError. Person 4 detection is incomplete."
            )

        decision = getattr(res, "identity_decision", None) or res.get(
            "identity_decision"
        )
        rule = getattr(res, "rule", None) or res.get("rule")
        score = getattr(res, "risk_score", None) or res.get("risk_score")
        sev = getattr(res, "severity", None) or res.get("severity")

        # 1. Identity Cleared
        if intended_label == "cleared_r1":
            if decision != "CLEARED_BY_IDENTITY" or rule != "R1_EXACT_ID":
                mismatches.append(
                    f"{f_id}: expected CLEARED_BY_IDENTITY/R1_EXACT_ID, got {decision}/{rule}"
                )
            counts["official_cleared"] += 1
        elif intended_label == "cleared_r2":
            if decision != "CLEARED_BY_IDENTITY" or rule != "R2_PUBLISHER_ID":
                mismatches.append(
                    f"{f_id}: expected CLEARED_BY_IDENTITY/R2_PUBLISHER_ID, got {decision}/{rule}"
                )
            counts["official_cleared"] += 1
        elif intended_label == "cleared_r3":
            if decision != "CLEARED_BY_IDENTITY" or rule != "R3_PARTNER":
                mismatches.append(
                    f"{f_id}: expected CLEARED_BY_IDENTITY/R3_PARTNER, got {decision}/{rule}"
                )
            counts["official_cleared"] += 1

        # 2. Benign Lookalikes
        elif intended_label.startswith("benign_"):
            if decision not in {"BENIGN_LOOKALIKE", "BELOW_THRESHOLD"}:
                mismatches.append(
                    f"{f_id}: expected BENIGN_LOOKALIKE/BELOW_THRESHOLD, got {decision}"
                )
            counts["benign_lookalike"] += 1

        # 3. Impersonation
        elif intended_label.startswith("impersonation_"):
            if decision != "CANDIDATE_FOR_REVIEW":
                mismatches.append(
                    f"{f_id}: expected CANDIDATE_FOR_REVIEW, got {decision}"
                )
            if f_id == "c-0028" and sev not in {"MEDIUM", "LOW"}:
                mismatches.append(
                    f"{f_id}: exact-name-only must be capped at MEDIUM, got severity {sev} (score {score})"
                )
            counts["findings"] += 1

        # 4. Not relevant
        elif intended_label == "not_relevant":
            if decision != "BELOW_THRESHOLD":
                mismatches.append(f"{f_id}: expected BELOW_THRESHOLD, got {decision}")
            counts["not_relevant"] += 1

    # Report any mismatches
    if mismatches:
        pytest.fail(
            "Scoring mismatches found against manifest:\n" + "\n".join(mismatches)
        )

    # Funnel invariant
    deduplicated = len(fixtures)
    assert deduplicated == (
        counts["official_cleared"]
        + counts["not_relevant"]
        + counts["benign_lookalike"]
        + counts["below_threshold"]
        + counts["findings"]
    )
