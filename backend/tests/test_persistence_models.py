"""Persistence and schema tests for ThreatLens v3 SQLAlchemy models."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

# Ensure backend package is in python path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.base import Base, generate_uuid, utc_now
from app.db.models import (
    AnalystDecision,
    Assessment,
    AuditEvent,
    Brand,
    CandidateAsset,
    EvaluationRun,
    Evidence,
    OfficialAsset,
    ResponseCache,
    Scan,
)
from app.db.session import (
    create_db_engine,
    init_db,
    mark_interrupted_scans,
)


@pytest.fixture
def sqlite_engine():
    """Create a fresh in-memory SQLite engine for tests."""
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    """Provide a database session bound to the test engine."""
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=sqlite_engine,
        class_=Session,
        expire_on_commit=False,
    )
    session = session_factory()
    yield session
    session.close()


def test_init_db_creates_all_ten_tables(sqlite_engine):
    """Test that init_db creates all 10 tables from Section 9 on empty SQLite."""
    inspector = inspect(sqlite_engine)
    tables = set(inspector.get_table_names())

    expected_tables = {
        "brands",
        "official_assets",
        "scans",
        "candidate_assets",
        "assessments",
        "evidence",
        "analyst_decisions",
        "audit_events",
        "response_cache",
        "evaluation_runs",
    }

    assert expected_tables.issubset(tables), (
        f"Missing tables: {expected_tables - tables}"
    )

    # Verify column existence and names for candidate_assets
    candidate_cols = {col["name"] for col in inspector.get_columns("candidate_assets")}
    required_candidate_cols = {
        "id",
        "brand_id",
        "platform",
        "asset_type",
        "stable_identifier",
        "secondary_identifiers",
        "display_name",
        "handle",
        "publisher_name",
        "developer_id",
        "description",
        "category",
        "external_links",
        "icon_url",
        "icon_hash",
        "canonical_url",
        "created_at_source",
        "followers",
        "following",
        "posts_count",
        "rating_count",
        "last_source_mode",
        "content_hash",
        "analyst_status",
        "analyst_reason",
        "first_seen_at",
        "last_seen_at",
        "last_scan_id",
    }
    assert required_candidate_cols.issubset(candidate_cols)


def test_unique_constraint_official_assets(db_session):
    """UNIQUE (brand_id, platform, stable_identifier) on official_assets must raise."""
    brand = Brand(
        name="Kaveri Bank",
        official_domains=["kaveribank.example"],
        keywords=["Kaveri Bank"],
        distinctive_tokens=["kaveri"],
        generic_tokens_extra=[],
        demo_brand=True,
    )
    db_session.add(brand)
    db_session.commit()

    asset1 = OfficialAsset(
        brand_id=brand.id,
        asset_type="IOS_APP",
        platform="apple_app_store",
        stable_identifier="1234567890",
        display_name="Kaveri Bank",
        relationship="OFFICIAL",
        verification_method="STORE_LOOKUP",
    )
    db_session.add(asset1)
    db_session.commit()

    asset2 = OfficialAsset(
        brand_id=brand.id,
        asset_type="IOS_APP",
        platform="apple_app_store",
        stable_identifier="1234567890",  # Duplicate stable_identifier for same brand & platform
        display_name="Kaveri Bank Duplicate",
        relationship="OFFICIAL",
        verification_method="STORE_LOOKUP",
    )
    db_session.add(asset2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_constraint_candidate_assets(db_session):
    """UNIQUE (brand_id, platform, stable_identifier) on candidate_assets must raise."""
    brand = Brand(
        name="Kaveri Bank",
        official_domains=["kaveribank.example"],
        keywords=["Kaveri Bank"],
        distinctive_tokens=["kaveri"],
        generic_tokens_extra=[],
        demo_brand=True,
    )
    db_session.add(brand)
    db_session.commit()

    cand1 = CandidateAsset(
        brand_id=brand.id,
        platform="apple_app_store",
        asset_type="IOS_APP",
        stable_identifier="9876543210",
        display_name="Kaveri Bank Rewards",
        last_source_mode="LIVE",
        content_hash="abc123hash",
    )
    db_session.add(cand1)
    db_session.commit()

    cand2 = CandidateAsset(
        brand_id=brand.id,
        platform="apple_app_store",
        asset_type="IOS_APP",
        stable_identifier="9876543210",  # Duplicate
        display_name="Kaveri Bank Rewards Dup",
        last_source_mode="LIVE",
        content_hash="def456hash",
    )
    db_session.add(cand2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_json_round_trips_correctly(sqlite_engine):
    """Test that JSON structures (lists, dicts, nested payloads) round-trip faithfully."""
    session_factory = sessionmaker(
        bind=sqlite_engine, class_=Session, expire_on_commit=False
    )

    brand_id = generate_uuid()
    domains = ["kaveribank.example", "online.kaveribank.example"]
    keywords = ["Kaveri Bank", "KaveriBank", "Kaveri Mobile"]
    distinctive = ["kaveri"]
    options_payload = {
        "asset_types": ["IOS_APP", "SOCIAL_ACCOUNT"],
        "source_ids": ["apple_itunes", "bluesky_public"],
        "query_limit_per_source": 25,
        "include_icon_similarity": True,
    }
    funnel_payload = {
        "retrieved": 53,
        "deduplicated": 49,
        "official_cleared": 2,
        "not_relevant": 31,
        "benign_lookalike": 7,
        "below_threshold": 3,
        "findings": 6,
    }
    events_payload = [
        {
            "at": "2026-10-12T05:30:12Z",
            "stage": "fetching",
            "message": "Query 1 executed",
        }
    ]

    # Session 1: Write
    with session_factory() as session:
        brand = Brand(
            id=brand_id,
            name="Kaveri Bank",
            official_domains=domains,
            keywords=keywords,
            distinctive_tokens=distinctive,
            generic_tokens_extra=[],
            demo_brand=True,
        )
        session.add(brand)

        scan = Scan(
            brand_id=brand_id,
            mode="LIVE",
            status="RUNNING",
            stage="fetching",
            progress_percent=40,
            options=options_payload,
            source_outcomes=[],
            funnel=funnel_payload,
            findings_by_severity={"HIGH": 2, "MEDIUM": 3},
            events=events_payload,
        )
        session.add(scan)
        session.commit()
        scan_id = scan.id

    # Session 2: Read & Verify
    with session_factory() as session:
        reloaded_brand = session.get(Brand, brand_id)
        assert reloaded_brand is not None
        assert isinstance(reloaded_brand.official_domains, list)
        assert reloaded_brand.official_domains == domains
        assert isinstance(reloaded_brand.keywords, list)
        assert reloaded_brand.keywords == keywords
        assert reloaded_brand.distinctive_tokens == distinctive

        reloaded_scan = session.get(Scan, scan_id)
        assert reloaded_scan is not None
        assert isinstance(reloaded_scan.options, dict)
        assert reloaded_scan.options == options_payload
        assert isinstance(reloaded_scan.funnel, dict)
        assert reloaded_scan.funnel == funnel_payload
        assert isinstance(reloaded_scan.events, list)
        assert reloaded_scan.events == events_payload


def test_timestamps_are_utc_aware_after_reload(sqlite_engine):
    """Test that timestamps are timezone-aware and set to UTC after being reloaded from DB."""
    session_factory = sessionmaker(
        bind=sqlite_engine, class_=Session, expire_on_commit=False
    )

    brand_id = generate_uuid()
    explicit_dt = datetime(2026, 10, 12, 5, 30, 0, tzinfo=UTC)

    # Session 1: Write with both default and explicit UTC datetimes
    with session_factory() as session:
        brand = Brand(
            id=brand_id,
            name="Kaveri Bank",
            created_at=explicit_dt,
            updated_at=utc_now(),
        )
        session.add(brand)
        session.commit()

    # Session 2: Read in a completely new session
    with session_factory() as session:
        reloaded = session.get(Brand, brand_id)
        assert reloaded is not None

        # Verify created_at
        assert reloaded.created_at is not None
        assert reloaded.created_at.tzinfo is not None, (
            "Timestamp must be timezone-aware"
        )
        assert reloaded.created_at.tzinfo == UTC
        assert reloaded.created_at == explicit_dt

        # Verify updated_at
        assert reloaded.updated_at is not None
        assert reloaded.updated_at.tzinfo is not None, (
            "Timestamp must be timezone-aware"
        )
        assert reloaded.updated_at.tzinfo == UTC


def test_mark_interrupted_scans_helper(db_session):
    """Test that mark_interrupted_scans marks RUNNING scans as FAILED with proper message."""
    brand = Brand(name="Kaveri Bank")
    db_session.add(brand)
    db_session.commit()

    scan1 = Scan(
        brand_id=brand.id,
        mode="LIVE",
        status="RUNNING",
        stage="fetching",
        progress_percent=50,
    )
    scan2 = Scan(
        brand_id=brand.id,
        mode="LIVE",
        status="COMPLETED",
        stage="completed",
        progress_percent=100,
    )
    scan3 = Scan(
        brand_id=brand.id,
        mode="LIVE",
        status="QUEUED",
        stage="queued",
        progress_percent=0,
    )
    db_session.add_all([scan1, scan2, scan3])
    db_session.commit()

    # Call mark_interrupted_scans
    updated_count = mark_interrupted_scans(db_session)
    assert updated_count == 1

    # Reload scan1
    db_session.refresh(scan1)
    assert scan1.status == "FAILED"
    assert scan1.error_message == "Interrupted by server restart"
    assert scan1.completed_at is not None
    assert scan1.completed_at.tzinfo == UTC

    # Reload other scans; ensure they were not modified
    db_session.refresh(scan2)
    assert scan2.status == "COMPLETED"
    db_session.refresh(scan3)
    assert scan3.status == "QUEUED"


def test_engine_postgres_sslmode_configuration():
    """Test that Postgres URL automatically adds sslmode=require in connect_args and pool_pre_ping."""
    from unittest.mock import MagicMock, patch

    from app.db.session import get_engine_options

    url, options = get_engine_options(
        "postgresql://user:pass@localhost:5432/threatlens"
    )
    assert url == "postgresql://user:pass@localhost:5432/threatlens"
    assert options["pool_pre_ping"] is True
    assert options["connect_args"]["sslmode"] == "require"

    with patch("app.db.session.create_engine") as mock_create_engine:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = create_db_engine("postgresql://user:pass@localhost:5432/threatlens")
        assert result == mock_engine
        mock_create_engine.assert_called_once_with(
            "postgresql://user:pass@localhost:5432/threatlens",
            pool_pre_ping=True,
            connect_args={"sslmode": "require"},
        )


def test_all_ten_models_crud_roundtrip(db_session):
    """Test full insertion, relationships, and queries across all 10 Section 9 tables."""
    # 1. Brand
    brand = Brand(
        name="Kaveri Bank",
        description="Fictional demo brand",
        official_domains=["kaveribank.example"],
        keywords=["Kaveri Bank", "KaveriBank"],
        distinctive_tokens=["kaveri"],
        generic_tokens_extra=[],
        industry_category="Finance",
        demo_brand=True,
    )
    db_session.add(brand)
    db_session.commit()

    # 2. OfficialAsset
    official_asset = OfficialAsset(
        brand_id=brand.id,
        asset_type="IOS_APP",
        platform="apple_app_store",
        stable_identifier="1234567890",
        secondary_identifiers={"bundle_id": "com.kaveribank.mobile"},
        developer_id="9000000001",
        publisher_name="Kaveri Bank Ltd",
        display_name="Kaveri Bank",
        relationship="OFFICIAL",
        verification_method="STORE_LOOKUP",
        is_verified=True,
        trust_publisher=True,
    )
    db_session.add(official_asset)
    db_session.commit()

    # 3. Scan
    scan = Scan(
        brand_id=brand.id,
        mode="LIVE",
        status="RUNNING",
        stage="fetching",
        progress_percent=25,
        options={"asset_types": ["IOS_APP"]},
        source_outcomes=[],
        funnel={},
        findings_by_severity={},
        events=[],
    )
    db_session.add(scan)
    db_session.commit()

    # 4. CandidateAsset
    candidate = CandidateAsset(
        brand_id=brand.id,
        platform="apple_app_store",
        asset_type="IOS_APP",
        stable_identifier="9876543210",
        secondary_identifiers={"bundle_id": "com.kaveribank.rewards"},
        display_name="Kaveri Bank Rewards",
        publisher_name="KB Rewards Studio",
        developer_id="9000000042",
        description="Rewards app",
        category="Finance",
        external_links=["https://kb-rewards.example"],
        last_source_mode="LIVE",
        content_hash="contenthash9876",
        analyst_status="NEW",
        first_seen_at=utc_now(),
        last_seen_at=utc_now(),
        last_scan_id=scan.id,
    )
    db_session.add(candidate)
    db_session.commit()

    # 5. Assessment
    assessment = Assessment(
        scan_id=scan.id,
        brand_id=brand.id,
        candidate_asset_id=candidate.id,
        identity_decision="CANDIDATE_FOR_REVIEW",
        rule="NO_EXACT_OR_PUBLISHER_MATCH",
        matched_official_asset_id=None,
        risk_score=72,
        severity="HIGH",
        evidence_coverage=1.0,
        corroborating_groups=["VISUAL", "CONTENT", "CONTEXT"],
        gates_applied=[],
        score_breakdown=[{"signal": "name_lookalike", "points": 19.5}],
        technique="ADDED_WORD",
        explanation="Candidate for review: similar name with added word.",
        source_mode="LIVE",
        scoring_version="3.0.0",
        nearest_official_asset_id=official_asset.id,
    )
    db_session.add(assessment)
    db_session.commit()

    # 6. Evidence
    evidence = Evidence(
        assessment_id=assessment.id,
        candidate_asset_id=candidate.id,
        scan_id=scan.id,
        source_id="apple_itunes",
        evidence_type="APP_STORE_METADATA",
        status="OBSERVED",
        field_name="publisher_name",
        observed_value="KB Rewards Studio",
        source_url="https://apps.apple.com/app/id9876543210",
        notes="Live search result",
    )
    db_session.add(evidence)
    db_session.commit()

    # 7. AnalystDecision
    decision = AnalystDecision(
        candidate_asset_id=candidate.id,
        assessment_id=assessment.id,
        previous_status="NEW",
        new_status="DISMISSED_FALSE_POSITIVE",
        decision_reason="Unrelated category and publisher.",
        notes="Hard negative",
        actor_label="analyst_1",
    )
    db_session.add(decision)
    db_session.commit()

    # 8. AuditEvent
    audit = AuditEvent(
        brand_id=brand.id,
        actor_label="analyst_1",
        event_type="ANALYST_DECISION_RECORDED",
        entity_type="candidate_assets",
        entity_id=candidate.id,
        details={"status": "DISMISSED_FALSE_POSITIVE"},
    )
    db_session.add(audit)
    db_session.commit()

    # 9. ResponseCache
    cache = ResponseCache(
        key="cache_key_hash_apple_123",
        source_id="apple_itunes",
        request={"term": "kaveri bank"},
        response={"resultCount": 1, "results": []},
        ttl_seconds=3600,
    )
    db_session.add(cache)
    db_session.commit()

    # 10. EvaluationRun
    eval_run = EvaluationRun(
        dataset_id="threatlens-v1",
        split="HELDOUT",
        scoring_version="3.0.0",
        config={"threshold": {"review": 25}},
        metrics={"precision": 0.94, "recall": 0.88, "f1": 0.91},
    )
    db_session.add(eval_run)
    db_session.commit()

    # Verify lookups and relationship traversals
    assert db_session.get(Brand, brand.id).name == "Kaveri Bank"
    assert len(db_session.get(Brand, brand.id).official_assets) == 1
    assert db_session.get(OfficialAsset, official_asset.id).brand.name == "Kaveri Bank"
    assert db_session.get(Scan, scan.id).brand.name == "Kaveri Bank"
    assert db_session.get(CandidateAsset, candidate.id).brand.name == "Kaveri Bank"
    assert db_session.get(Assessment, assessment.id).risk_score == 72
    assert (
        db_session.get(Assessment, assessment.id).candidate_asset.display_name
        == "Kaveri Bank Rewards"
    )
    assert db_session.get(Evidence, evidence.id).field_name == "publisher_name"
    assert (
        db_session.get(AnalystDecision, decision.id).new_status
        == "DISMISSED_FALSE_POSITIVE"
    )
    assert db_session.get(AuditEvent, audit.id).entity_id == candidate.id
    assert (
        db_session.get(ResponseCache, "cache_key_hash_apple_123").source_id
        == "apple_itunes"
    )
    assert db_session.get(EvaluationRun, eval_run.id).dataset_id == "threatlens-v1"


def test_indexes_exist_on_all_required_columns(sqlite_engine):
    """Verify indexes on (brand_id, status), (brand_id, platform), (scan_id), (candidate_asset_id)."""
    inspector = inspect(sqlite_engine)

    # Scans: (brand_id, status)
    scans_indexes = inspector.get_indexes("scans")
    scans_cols = [idx["column_names"] for idx in scans_indexes]
    assert ["brand_id", "status"] in scans_cols

    # Official Assets: (brand_id, platform)
    oa_indexes = inspector.get_indexes("official_assets")
    oa_cols = [idx["column_names"] for idx in oa_indexes]
    assert ["brand_id", "platform"] in oa_cols

    # Candidate Assets: (brand_id, platform), (brand_id, analyst_status), (last_scan_id)
    ca_indexes = inspector.get_indexes("candidate_assets")
    ca_cols = [idx["column_names"] for idx in ca_indexes]
    assert ["brand_id", "platform"] in ca_cols
    assert ["brand_id", "analyst_status"] in ca_cols
    assert ["last_scan_id"] in ca_cols

    # Assessments: (scan_id), (candidate_asset_id)
    ass_indexes = inspector.get_indexes("assessments")
    ass_cols = [idx["column_names"] for idx in ass_indexes]
    assert ["scan_id"] in ass_cols
    assert ["candidate_asset_id"] in ass_cols

    # Evidence: (scan_id), (candidate_asset_id)
    ev_indexes = inspector.get_indexes("evidence")
    ev_cols = [idx["column_names"] for idx in ev_indexes]
    assert ["scan_id"] in ev_cols
    assert ["candidate_asset_id"] in ev_cols

    # Analyst Decisions: (candidate_asset_id)
    ad_indexes = inspector.get_indexes("analyst_decisions")
    ad_cols = [idx["column_names"] for idx in ad_indexes]
    assert ["candidate_asset_id"] in ad_cols


def test_init_db_on_sqlite_file(tmp_path):
    """Test init_db creates all tables on a fresh SQLite disk file."""
    db_file = tmp_path / "test_init.db"
    file_engine = create_db_engine(f"sqlite:///{db_file}")
    init_db(file_engine)

    inspector = inspect(file_engine)
    tables = inspector.get_table_names()
    assert "brands" in tables
    assert "scans" in tables
    assert "candidate_assets" in tables
    file_engine.dispose()


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set (Postgres tests skipped)",
)
def test_postgres_model_conformance():
    """Definition-of-Done verification on live Supabase Postgres database.

    Verifies:
    1. create_all creates all 10 tables and required indexes.
    2. JSON columns round-trip correctly.
    3. UUID strings are stable.
    4. Timestamps stay timezone-aware UTC.
    5. Unique constraints raise IntegrityError.
    """
    pg_url = os.environ["TEST_DATABASE_URL"]
    engine = create_db_engine(pg_url)

    # 1. create_all
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    expected = {
        "brands",
        "official_assets",
        "scans",
        "candidate_assets",
        "assessments",
        "evidence",
        "analyst_decisions",
        "audit_events",
        "response_cache",
        "evaluation_runs",
    }
    assert expected.issubset(tables), f"Missing tables on Postgres: {expected - tables}"

    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    with session_factory() as session:
        # 2 & 3. Create Brand with deterministic UUID and rich JSON
        brand_id = generate_uuid()
        fixed_dt = datetime(2026, 10, 12, 14, 30, 0, tzinfo=UTC)
        test_json = ["kaveribank.example", "online.kaveribank.example"]

        brand = Brand(
            id=brand_id,
            name="Supabase QA Brand",
            description="Testing Postgres round-trip",
            official_domains=test_json,
            keywords=["kaveri", "bank"],
            distinctive_tokens=["kaveri"],
            generic_tokens_extra=["bank"],
            industry_category="Banking",
            created_at=fixed_dt,
        )
        session.add(brand)

        # Official asset
        asset_id = generate_uuid()
        official_asset = OfficialAsset(
            id=asset_id,
            brand_id=brand_id,
            asset_type="IOS_APP",
            platform="apple_app_store",
            stable_identifier="1234567890",
            secondary_identifiers={"bundle_id": "com.kaveribank.mobile"},
            display_name="Kaveri Bank Official",
            relationship="OFFICIAL",
            verification_method="DOMAIN_DNS",
            created_at=fixed_dt,
        )
        session.add(official_asset)
        session.commit()

        # 3. UUID stability & JSON round-trip & UTC timestamp verification
        reloaded_brand = session.get(Brand, brand_id)
        assert reloaded_brand is not None
        assert reloaded_brand.id == brand_id
        assert reloaded_brand.official_domains == test_json
        assert reloaded_brand.created_at.tzinfo is not None
        assert reloaded_brand.created_at.utcoffset().total_seconds() == 0

        # 5. Unique constraint enforcement
        duplicate_asset = OfficialAsset(
            id=generate_uuid(),
            brand_id=brand_id,
            asset_type="IOS_APP",
            platform="apple_app_store",
            stable_identifier="1234567890",  # Duplicate (brand_id, platform, stable_identifier)
            secondary_identifiers={},
            display_name="Duplicate Asset",
            relationship="OFFICIAL",
            verification_method="DOMAIN_DNS",
        )
        session.add(duplicate_asset)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    # Clean up
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
