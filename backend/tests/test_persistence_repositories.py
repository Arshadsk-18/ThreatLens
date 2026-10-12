"""Shared repository persistence test suite verifying identical behavior across in-memory and SQLAlchemy."""

from __future__ import annotations

import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

# Ensure backend package is in python path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.base import Base
from app.db.session import create_db_engine
from app.repositories import (
    DomainValidationError,
    RepositoryBundle,
    compute_content_hash,
    create_in_memory_repositories,
    create_sqlalchemy_repositories,
)


@pytest.fixture(
    params=[
        "in_memory",
        "sqlalchemy_sqlite",
        pytest.param(
            "sqlalchemy_postgres",
            marks=pytest.mark.skipif(
                not os.getenv("TEST_DATABASE_URL"),
                reason="TEST_DATABASE_URL not set (Postgres tests skipped)",
            ),
        ),
    ]
)
def repos(request, tmp_path) -> RepositoryBundle:
    """Fixture parameterized over repository backends to prove identical behavior."""
    kind = request.param

    if kind == "in_memory":
        yield create_in_memory_repositories()

    elif kind == "sqlalchemy_sqlite":
        db_file = (
            tmp_path
            / f"test_repo_{request.node.name.replace('[', '_').replace(']', '_')}.db"
        )
        engine = create_db_engine(f"sqlite:///{db_file}")
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            class_=Session,
            expire_on_commit=False,
        )
        bundle = create_sqlalchemy_repositories(session_factory)
        yield bundle
        engine.dispose()

    elif kind == "sqlalchemy_postgres":
        pg_url = os.environ["TEST_DATABASE_URL"]
        engine = create_db_engine(pg_url)
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            class_=Session,
            expire_on_commit=False,
        )
        bundle = create_sqlalchemy_repositories(session_factory)
        yield bundle
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_brand_and_asset_crud_and_audit(repos: RepositoryBundle):
    """Test brand creation, asset registry, unique constraint, and automatic audit logging."""
    # 1. Create brand
    brand = repos.brand_repo.create(
        {
            "name": "Kaveri Bank",
            "description": "Fictional demo bank",
            "official_domains": ["kaveribank.example"],
            "keywords": ["Kaveri Bank"],
            "distinctive_tokens": ["kaveri"],
            "demo_brand": True,
        }
    )
    brand_id = brand["id"]
    assert brand["name"] == "Kaveri Bank"

    # 2. Register official asset
    asset1 = repos.asset_repo.create(
        {
            "brand_id": brand_id,
            "asset_type": "IOS_APP",
            "platform": "apple_app_store",
            "stable_identifier": "1234567890",
            "display_name": "Kaveri Bank Official",
            "relationship": "OFFICIAL",
            "verification_method": "STORE_LOOKUP",
            "is_verified": True,
        },
        actor_label="admin_1",
    )
    assert asset1["stable_identifier"] == "1234567890"

    # 3. Duplicate asset with same (brand_id, platform, stable_identifier) must raise DomainValidationError
    with pytest.raises(DomainValidationError):
        repos.asset_repo.create(
            {
                "brand_id": brand_id,
                "asset_type": "IOS_APP",
                "platform": "apple_app_store",
                "stable_identifier": "1234567890",
                "display_name": "Kaveri Bank Duplicate",
                "relationship": "OFFICIAL",
                "verification_method": "STORE_LOOKUP",
            }
        )

    # 4. Update asset
    updated_asset = repos.asset_repo.update(
        asset1["id"],
        {"display_name": "Kaveri Bank Mobile Pro"},
        actor_label="admin_2",
    )
    assert updated_asset["display_name"] == "Kaveri Bank Mobile Pro"

    # 5. Confirm audit log recorded creation and update
    audit_page = repos.audit_repo.list(brand_id=brand_id)
    assert audit_page.total >= 2
    event_types = [e.event_type for e in audit_page.items]
    assert "OFFICIAL_ASSET_CREATED" in event_types
    assert "OFFICIAL_ASSET_UPDATED" in event_types


def test_scan_lifecycle_and_event_capping(repos: RepositoryBundle):
    """Test scan creation, progress updates, event log capping at 200, and completion."""
    brand = repos.brand_repo.create({"name": "Scan Test Bank"})
    brand_id = brand["id"]

    scan = repos.scan_repo.create(
        {
            "brand_id": brand_id,
            "mode": "LIVE",
            "status": "QUEUED",
            "stage": "queued",
            "options": {"query_limit": 25},
        }
    )
    scan_id = scan["id"]
    assert scan["status"] == "QUEUED"

    # Update progress
    updated_scan = repos.scan_repo.update_progress(
        scan_id, stage="fetching", progress_percent=30
    )
    assert updated_scan["stage"] == "fetching"
    assert updated_scan["progress_percent"] == 30

    # Append 250 events (must be capped at 200 events)
    for i in range(250):
        repos.scan_repo.append_event(
            scan_id,
            {
                "at": datetime.now(UTC).isoformat(),
                "stage": "fetching",
                "level": "INFO",
                "message": f"Query execution index {i}",
            },
        )

    reloaded_scan = repos.scan_repo.get(scan_id)
    assert len(reloaded_scan["events"]) == 200
    assert "Query execution index 249" in reloaded_scan["events"][-1]["message"]

    # Finish scan
    finished = repos.scan_repo.finish(
        scan_id=scan_id,
        status="COMPLETED",
        source_outcomes=[{"source_id": "apple_itunes", "status": "CONNECTED"}],
        funnel={"retrieved": 50, "findings": 5},
        findings_by_severity={"HIGH": 2, "MEDIUM": 3},
    )
    assert finished["status"] == "COMPLETED"
    assert finished["progress_percent"] == 100
    assert finished["completed_at"] is not None


def test_candidate_race_safe_upsert_and_content_hash(repos: RepositoryBundle):
    """Test candidate upsert preserves decision memory and correctly calculates content_hash."""
    brand = repos.brand_repo.create({"name": "Kaveri Bank"})
    brand_id = brand["id"]
    scan = repos.scan_repo.create({"brand_id": brand_id, "mode": "LIVE"})
    scan_id = scan["id"]

    expected_hash = compute_content_hash(
        display_name="Kaveri Bank Rewards",
        publisher_name="KB Rewards Studio",
        description="Earn reward points.",
        icon_hash="iconhash123",
    )

    candidate_input = {
        "platform": "apple_app_store",
        "asset_type": "IOS_APP",
        "stable_identifier": "9876543210",
        "display_name": "Kaveri Bank Rewards",
        "publisher_name": "KB Rewards Studio",
        "description": "Earn reward points.",
        "icon_hash": "iconhash123",
        "category": "Finance",
        "source_mode": "LIVE",
    }

    # 1. First upsert creates row
    cand1 = repos.candidate_repo.upsert(
        candidate_input, brand_id=brand_id, scan_id=scan_id
    )
    assert cand1["stable_identifier"] == "9876543210"
    assert cand1["content_hash"] == expected_hash
    assert cand1["analyst_status"] == "NEW"
    first_seen = cand1["first_seen_at"]

    # 2. Second upsert with updated category and different scan_id
    scan2 = repos.scan_repo.create({"brand_id": brand_id, "mode": "LIVE"})
    candidate_input_updated = dict(candidate_input)
    candidate_input_updated["category"] = "Shopping"

    cand2 = repos.candidate_repo.upsert(
        candidate_input_updated, brand_id=brand_id, scan_id=scan2["id"]
    )
    assert cand2["id"] == cand1["id"]
    assert cand2["category"] == "Shopping"
    assert cand2["last_scan_id"] == scan2["id"]
    assert cand2["first_seen_at"] == first_seen
    assert cand2["analyst_status"] == "NEW"


def test_decision_repo_atomic_validation_and_audit(repos: RepositoryBundle):
    """Test DecisionRepo validates reason for dismissals, updates candidate, and logs audit atomically."""
    brand = repos.brand_repo.create({"name": "Kaveri Bank"})
    scan = repos.scan_repo.create({"brand_id": brand["id"], "mode": "LIVE"})
    cand = repos.candidate_repo.upsert(
        {
            "platform": "apple_app_store",
            "asset_type": "IOS_APP",
            "stable_identifier": "9876543210",
            "display_name": "Kaveri Rewards",
        },
        brand_id=brand["id"],
        scan_id=scan["id"],
    )

    # Missing decision_reason for DISMISSED_FALSE_POSITIVE must raise DomainValidationError
    with pytest.raises(DomainValidationError):
        repos.decision_repo.record(
            candidate_id=cand["id"],
            assessment_id=None,
            new_status="DISMISSED_FALSE_POSITIVE",
            decision_reason="",  # empty reason
        )

    # Missing decision_reason for CONFIRMED_SUSPICIOUS must raise DomainValidationError
    with pytest.raises(DomainValidationError):
        repos.decision_repo.record(
            candidate_id=cand["id"],
            assessment_id=None,
            new_status="CONFIRMED_SUSPICIOUS",
            decision_reason="   ",  # whitespace only
        )

    # Verify candidate analyst_status remained NEW (no partial write)
    reloaded_cand = repos.candidate_repo.get(cand["id"])
    assert reloaded_cand["analyst_status"] == "NEW"

    # Valid decision succeeds and writes decision row + audit event
    decision_row = repos.decision_repo.record(
        candidate_id=cand["id"],
        assessment_id=None,
        new_status="DISMISSED_FALSE_POSITIVE",
        decision_reason="Unrelated category and publisher.",
        notes="Hard negative verification",
        actor_label="analyst_alice",
    )
    assert decision_row["new_status"] == "DISMISSED_FALSE_POSITIVE"
    assert decision_row["previous_status"] == "NEW"

    reloaded_cand = repos.candidate_repo.get(cand["id"])
    assert reloaded_cand["analyst_status"] == "DISMISSED_FALSE_POSITIVE"
    assert reloaded_cand["analyst_reason"] == "Unrelated category and publisher."

    # Audit row exists
    audit_page = repos.audit_repo.list(brand_id=brand["id"])
    assert any(a.event_type == "ANALYST_DECISION" for a in audit_page.items)


def test_decision_memory_persists(repos: RepositoryBundle):
    """Test full decision memory lifecycle: dismiss, suppress on identical rescan, resurface on content change."""
    brand = repos.brand_repo.create({"name": "Kaveri Bank"})
    brand_id = brand["id"]

    # 1. Scan 1 finds candidate C1
    scan1 = repos.scan_repo.create({"brand_id": brand_id, "mode": "LIVE"})
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
    cand = repos.candidate_repo.upsert(
        candidate_data, brand_id=brand_id, scan_id=scan1["id"]
    )

    assessment1_id = repos.assessment_repo.save(
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

    # 2. Finding appears in findings queue
    page1 = repos.assessment_repo.list_findings(brand_id=brand_id, scan_id=scan1["id"])
    assert page1.total == 1
    assert page1.items[0].id == assessment1_id
    assert page1.items[0].changed_since_decision is False

    # 3. Analyst dismisses C1
    repos.decision_repo.record(
        candidate_id=cand["id"],
        assessment_id=assessment1_id,
        new_status="DISMISSED_FALSE_POSITIVE",
        decision_reason="Verified official loyalty rewards program.",
        actor_label="senior_analyst",
    )

    # 4. Scan 2 runs, upserts candidate C1 with IDENTICAL content
    scan2 = repos.scan_repo.create({"brand_id": brand_id, "mode": "LIVE"})
    cand_s2 = repos.candidate_repo.upsert(
        candidate_data, brand_id=brand_id, scan_id=scan2["id"]
    )
    assert cand_s2["analyst_status"] == "DISMISSED_FALSE_POSITIVE"

    assessment2_id = repos.assessment_repo.save(
        scan_id=scan2["id"],
        candidate_id=cand["id"],
        result={
            "identity_decision": "CANDIDATE_FOR_REVIEW",
            "risk_score": 72,
            "severity": "HIGH",
            "technique": "ADDED_WORD",
        },
        evidence=[],
        brand_id=brand_id,
    )

    # 5. Dismissed candidate is HIDDEN by default on Scan 2
    page2_hidden = repos.assessment_repo.list_findings(
        brand_id=brand_id, scan_id=scan2["id"], include_dismissed=False
    )
    assert page2_hidden.total == 0

    # 6. Candidate is visible when include_dismissed=True with changed_since_decision=False
    page2_shown = repos.assessment_repo.list_findings(
        brand_id=brand_id, scan_id=scan2["id"], include_dismissed=True
    )
    assert page2_shown.total == 1
    assert page2_shown.items[0].id == assessment2_id
    assert page2_shown.items[0].changed_since_decision is False

    # 7. Scan 3 runs, candidate CHANGED description (malicious update lure terms)
    scan3 = repos.scan_repo.create({"brand_id": brand_id, "mode": "LIVE"})
    changed_candidate_data = dict(candidate_data)
    changed_candidate_data["description"] = (
        "Urgent KYC update and netbanking login portal."
    )

    cand_s3 = repos.candidate_repo.upsert(
        changed_candidate_data, brand_id=brand_id, scan_id=scan3["id"]
    )
    assert cand_s3["content_hash"] != cand["content_hash"]

    assessment3_id = repos.assessment_repo.save(
        scan_id=scan3["id"],
        candidate_id=cand["id"],
        result={
            "identity_decision": "CANDIDATE_FOR_REVIEW",
            "risk_score": 85,
            "severity": "HIGH",
            "technique": "ADDED_WORD",
        },
        evidence=[],
        brand_id=brand_id,
    )

    # 8. RESURFACES with changed_since_decision=True even with include_dismissed=False!
    page3 = repos.assessment_repo.list_findings(
        brand_id=brand_id, scan_id=scan3["id"], include_dismissed=False
    )
    assert page3.total == 1
    assert page3.items[0].id == assessment3_id
    assert page3.items[0].changed_since_decision is True

    # 9. Confirm audit events trail exists
    audit_page = repos.audit_repo.list(brand_id=brand_id)
    assert audit_page.total >= 1
    assert any(
        a.details.get("new_status") == "DISMISSED_FALSE_POSITIVE"
        for a in audit_page.items
    )


def test_latest_only_returns_newest_assessment_per_candidate(repos: RepositoryBundle):
    """Test list_findings(latest_only=True) returns the newest assessment per candidate."""
    brand = repos.brand_repo.create({"name": "Kaveri Bank"})
    brand_id = brand["id"]

    scan1 = repos.scan_repo.create({"brand_id": brand_id, "mode": "LIVE"})
    scan2 = repos.scan_repo.create({"brand_id": brand_id, "mode": "LIVE"})

    cand1 = repos.candidate_repo.upsert(
        {
            "platform": "apple_app_store",
            "stable_identifier": "1001",
            "display_name": "App 1",
        },
        brand_id=brand_id,
        scan_id=scan1["id"],
    )
    cand2 = repos.candidate_repo.upsert(
        {
            "platform": "apple_app_store",
            "stable_identifier": "1002",
            "display_name": "App 2",
        },
        brand_id=brand_id,
        scan_id=scan1["id"],
    )

    # Candidate 1: Assessment 1 (score 40) then Assessment 2 (score 75)
    repos.assessment_repo.save(
        scan_id=scan1["id"],
        candidate_id=cand1["id"],
        result={
            "identity_decision": "CANDIDATE_FOR_REVIEW",
            "risk_score": 40,
            "technique": "NONE",
        },
        evidence=[],
        brand_id=brand_id,
    )
    time.sleep(0.01)  # ensure timestamp order
    ass1_latest_id = repos.assessment_repo.save(
        scan_id=scan2["id"],
        candidate_id=cand1["id"],
        result={
            "identity_decision": "CANDIDATE_FOR_REVIEW",
            "risk_score": 75,
            "technique": "NONE",
        },
        evidence=[],
        brand_id=brand_id,
    )

    # Candidate 2: Assessment 3 (score 60)
    ass2_id = repos.assessment_repo.save(
        scan_id=scan1["id"],
        candidate_id=cand2["id"],
        result={
            "identity_decision": "CANDIDATE_FOR_REVIEW",
            "risk_score": 60,
            "technique": "NONE",
        },
        evidence=[],
        brand_id=brand_id,
    )

    # With latest_only=True: exactly 2 findings returned (newest per candidate)
    latest_page = repos.assessment_repo.list_findings(
        brand_id=brand_id, latest_only=True
    )
    assert latest_page.total == 2
    found_ids = {f.id for f in latest_page.items}
    assert found_ids == {ass1_latest_id, ass2_id}

    # With latest_only=False: all 3 assessments returned
    all_page = repos.assessment_repo.list_findings(brand_id=brand_id, latest_only=False)
    assert all_page.total == 3


def test_cache_repo_ttl_and_stale_read(repos: RepositoryBundle):
    """Test CacheRepo TTL expiry, overwrite, and stale read behavior."""
    key = "cache_apple_search_kaveri"
    request_data = {"term": "kaveri bank", "limit": 10}
    response_data = {"resultCount": 2, "results": ["app1", "app2"]}

    # Put item with 1 second TTL
    repos.cache_repo.put(
        key=key,
        source_id="apple_itunes",
        request=request_data,
        response=response_data,
        ttl_seconds=1,
    )

    # Immediate get with max_age_s=10 returns item
    item = repos.cache_repo.get(key, max_age_s=10)
    assert item is not None
    assert item.response == response_data

    # Overwrite test
    response_updated = {"resultCount": 3, "results": ["app1", "app2", "app3"]}
    repos.cache_repo.put(
        key=key,
        source_id="apple_itunes",
        request=request_data,
        response=response_updated,
        ttl_seconds=1,
    )
    item_updated = repos.cache_repo.get(key, max_age_s=10)
    assert item_updated is not None
    assert item_updated.response == response_updated

    # When max_age_s is 0, item is considered expired -> returns None
    assert repos.cache_repo.get(key, max_age_s=0) is None

    # When max_age_s is None: stale read is permitted!
    stale_item = repos.cache_repo.get(key, max_age_s=None)
    assert stale_item is not None
    assert stale_item.response == response_updated


def test_list_cleared_filters_and_returns_page(repos: RepositoryBundle):
    """Test list_cleared returns only cleared decisions with proper filtering and pagination."""
    brand = repos.brand_repo.create({"name": "Kaveri Bank"})
    brand_id = brand["id"]

    scan = repos.scan_repo.create({"brand_id": brand_id, "mode": "LIVE"})
    scan_id = scan["id"]

    cand_official = repos.candidate_repo.upsert(
        {
            "platform": "apple_app_store",
            "stable_identifier": "1234567890",
            "display_name": "Kaveri Bank",
        },
        brand_id=brand_id,
        scan_id=scan_id,
    )
    cand_namesake = repos.candidate_repo.upsert(
        {
            "platform": "bluesky",
            "stable_identifier": "did:plc:kaveri",
            "display_name": "Kaveri Coffee Roasters",
        },
        brand_id=brand_id,
        scan_id=scan_id,
    )

    # 1. Official Exact Match
    repos.assessment_repo.save(
        scan_id=scan_id,
        candidate_id=cand_official["id"],
        result={
            "identity_decision": "OFFICIAL_EXACT_MATCH",
            "rule": "R1_EXACT_ID",
            "explanation": "Exact bundle ID match.",
        },
        evidence=[],
        brand_id=brand_id,
    )

    # 2. Benign Lookalike
    repos.assessment_repo.save(
        scan_id=scan_id,
        candidate_id=cand_namesake["id"],
        result={
            "identity_decision": "BENIGN_LOOKALIKE",
            "rule": "G4_LOW_CONTENT_OVERLAP",
            "explanation": "Unrelated category and publisher.",
        },
        evidence=[],
        brand_id=brand_id,
    )

    cleared_page = repos.assessment_repo.list_cleared(brand_id=brand_id)
    assert cleared_page.total == 2

    # Filter by decision
    official_only = repos.assessment_repo.list_cleared(
        brand_id=brand_id, decision="OFFICIAL_EXACT_MATCH"
    )
    assert official_only.total == 1
    assert official_only.items[0].decision == "OFFICIAL_EXACT_MATCH"
    assert official_only.items[0].rule == "R1_EXACT_ID"

    # Filter by platform
    bluesky_only = repos.assessment_repo.list_cleared(
        brand_id=brand_id, platform="bluesky"
    )
    assert bluesky_only.total == 1
    assert bluesky_only.items[0].decision == "BENIGN_LOOKALIKE"
