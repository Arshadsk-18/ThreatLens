"""Tests for evidence report building and formula-safe CSV export."""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

# Ensure backend package is in python path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.db.base import Base
from app.db.seed.seed import seed_demo_story
from app.repositories.export import (
    FORMULA_PREFIXES,
    LIMITATIONS_DISCLAIMER,
    build_evidence_report,
    findings_to_csv,
    sanitize_csv_cell,
)
from app.repositories.protocols import EntityNotFoundError
from app.repositories.sqlalchemy_repo import (
    SqlAlchemyAssessmentRepo,
    SqlAlchemyCandidateRepo,
    SqlAlchemyDecisionRepo,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def test_db_session_factory():
    """Create an in-memory SQLite database populated with demo data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    seed_demo_story(session_factory=session_factory, engine=engine)
    return session_factory


def test_sanitize_csv_cell():
    """Verify that formula injection prefixes are properly sanitized."""
    assert sanitize_csv_cell("Normal Text") == "Normal Text"
    assert sanitize_csv_cell(123) == "123"
    assert sanitize_csv_cell(None) == ""

    # Dangerous formula prefixes
    for prefix in FORMULA_PREFIXES:
        payload = f"{prefix}calc|' /C calc'!A0"
        sanitized = sanitize_csv_cell(payload)
        assert sanitized.startswith("'"), f"Failed to sanitize prefix {prefix!r}"
        assert sanitized == f"'{payload}"


def test_build_evidence_report(test_db_session_factory):
    """Verify that build_evidence_report returns complete factual stored data."""
    assessment_repo = SqlAlchemyAssessmentRepo(test_db_session_factory)
    decision_repo = SqlAlchemyDecisionRepo(test_db_session_factory)

    # Get one finding from the demo seed
    page = assessment_repo.list_findings(limit=1)
    assert page.total > 0
    finding = page.items[0]
    finding_id = finding.id
    candidate_id = finding.candidate_asset_id

    # Add a mock analyst decision to test decision history
    decision_repo.record(
        candidate_id=candidate_id,
        assessment_id=finding_id,
        new_status="CONFIRMED_SUSPICIOUS",
        decision_reason="Confirmed phishing lure with brand impersonation",
        notes="High risk confirmed by tier-2 review",
        actor_label="analyst_jane",
    )

    report = build_evidence_report(
        finding_id=finding_id, session_factory=test_db_session_factory
    )

    assert report["finding_id"] == finding_id
    assert report["risk_score"] == finding.risk_score
    assert report["severity"] == finding.severity
    assert report["technique"] == finding.technique
    assert "candidate" in report
    assert report["candidate"]["id"] == candidate_id
    assert report["candidate"]["display_name"] == finding.candidate.get("display_name")

    # Official asset compared
    assert "official_asset" in report
    # Identity guard
    assert "identity_guard" in report
    assert report["identity_guard"]["rule"] is not None
    # Score breakdown & gates
    assert "score_breakdown" in report
    assert "gates" in report
    assert "evidence_coverage" in report
    # Evidence rows
    assert "evidence_rows" in report
    assert len(report["evidence_rows"]) >= 1
    ev_item = report["evidence_rows"][0]
    assert "source_id" in ev_item
    assert "evidence_type" in ev_item
    assert "observed_at" in ev_item

    # Decision history
    assert len(report["decision_history"]) == 1
    dec = report["decision_history"][0]
    assert dec["new_status"] == "CONFIRMED_SUSPICIOUS"
    assert dec["decision_reason"] == "Confirmed phishing lure with brand impersonation"
    assert dec["actor_label"] == "analyst_jane"

    # Limitations disclaimer
    assert report["limitations"] == LIMITATIONS_DISCLAIMER
    assert "scoring_version" in report
    assert "source_mode" in report

    # Test non-existent finding raises EntityNotFoundError
    with pytest.raises(EntityNotFoundError):
        build_evidence_report(
            finding_id="00000000-0000-0000-0000-nonexistent",
            session_factory=test_db_session_factory,
        )


def test_findings_to_csv_formula_injection_defense(test_db_session_factory):
    """Verify that findings_to_csv sanitizes malicious formula cells."""
    candidate_repo = SqlAlchemyCandidateRepo(test_db_session_factory)
    assessment_repo = SqlAlchemyAssessmentRepo(test_db_session_factory)

    # Insert malicious candidates
    malicious_inputs = [
        ("=cmd|'/C calc'!A0", "+123456789", "m1"),
        ("@SUM(A1:A10)", "-500", "m2"),
        ("\tmalicious_tab", "\rmalicious_cr", "m3"),
    ]

    brand_id = "test-brand-csv-defense"
    scan_id = "00000000-0000-4000-8000-000000000001"

    for name, pub, stable_id in malicious_inputs:
        cand = candidate_repo.upsert(
            candidate={
                "source_id": "test",
                "platform": "apple_app_store",
                "asset_type": "IOS_APP",
                "stable_identifier": stable_id,
                "display_name": name,
                "publisher_name": pub,
                "source_mode": "SIMULATED",
            },
            brand_id=brand_id,
            scan_id=scan_id,
        )

        assessment_repo.save(
            scan_id=scan_id,
            candidate_id=cand["id"],
            result={
                "identity_decision": "CANDIDATE_FOR_REVIEW",
                "rule": "SUSPICIOUS_IMPERSONATION",
                "risk_score": 75,
                "severity": "HIGH",
                "technique": "ADDED_WORD",
                "explanation": f"Malicious input test: {name}",
                "source_mode": "SIMULATED",
            },
            evidence=[],
            brand_id=brand_id,
        )

    csv_data = findings_to_csv(
        brand_id=brand_id, session_factory=test_db_session_factory
    )

    # Check raw string: formulas must be prefixed with single quote
    assert "'=cmd|'/C calc'!A0" in csv_data
    assert "'+123456789" in csv_data
    assert "'@SUM(A1:A10)" in csv_data
    assert "'-500" in csv_data
    assert "'\tmalicious_tab" in csv_data
    assert "'\rmalicious_cr" in csv_data

    # Check that CSV is valid RFC 4180
    reader = csv.reader(io.StringIO(csv_data))
    rows = list(reader)
    header = rows[0]
    assert header[0] == "finding_id"
    assert "display_name" in header

    # Verify rows parsed properly
    for row in rows[1:]:
        name_val = row[header.index("display_name")]
        if name_val.startswith(tuple(FORMULA_PREFIXES)):
            pytest.fail(f"Unsanitized formula cell found: {name_val}")
