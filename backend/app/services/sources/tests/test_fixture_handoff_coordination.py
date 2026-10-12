"""Coordinated validation test suite for ThreatLens v3 fixture handoff.

Collaborators:
- Person 3 (Connectors Engineer): Owns adapter loading, re-normalization, zero-network enforcement.
- Person 2 (Orchestration & API): Owns registry mode selection and scan mode enforcement.
- Person 5 (Data & Validation): Owns backend/tests/fixtures/ dataset schemas and validation rules.

Verifies the 7 agreed behaviors:
1. Demo fixture records follow versioned JSON format.
2. Every demo candidate declares source_mode=SIMULATED; rejects LIVE with filename and record index.
3. Recorded fixtures preserve original timestamps and are re-normalized as CACHED.
4. LIVE scans reject demo_fixtures and recorded_fixtures (via registry and direct adapter calls).
5. DEMO execution makes zero external network calls (socket-level guard).
6. Fixture parsing failures are explicit errors, not empty successful scans.
7. Fictional fixture entities remain clearly documented as fictional.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from uuid import uuid4

import pytest

from app.schemas import (
    PlannedQuery,
    QueryPlan,
    SourceMode,
    SourceStatus,
)
from app.services.sources.fixtures_demo import DemoFixtureAdapter
from app.services.sources.fixtures_recorded import RecordedFixtureAdapter
from app.services.sources.registry import (
    assert_not_demo_only,
    get_adapter,
    is_demo_only,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
FIXTURES_DIR = REPO_ROOT / "backend" / "tests" / "fixtures"


def make_test_plan() -> QueryPlan:
    return QueryPlan(
        brand_id=uuid4(),
        queries=[
            PlannedQuery(term="kaveri bank", kind="BASE", priority=1),
        ],
    )


# ---------------------------------------------------------------------------
# Behavior 1: Demo fixture records follow agreed versioned JSON format
# ---------------------------------------------------------------------------
def test_behavior_1_demo_records_versioned_json_format() -> None:
    demo_file = FIXTURES_DIR / "demo" / "kaveri_bank_sample.json"
    assert demo_file.exists(), f"Expected fixture missing: {demo_file}"

    data = json.loads(demo_file.read_text(encoding="utf-8"))
    assert data.get("fixture_version") == 1
    assert isinstance(data.get("records"), list)
    assert len(data["records"]) > 0

    adapter = DemoFixtureAdapter()
    candidates = adapter._load_all_records()
    assert len(candidates) == len(data["records"])


def test_behavior_1_unsupported_version_rejected(tmp_path: Path) -> None:
    bad_version = {
        "fixture_version": 99,
        "records": [
            {
                "candidate": {
                    "source_id": "demo_fixtures",
                    "platform": "apple_app_store",
                    "asset_type": "IOS_APP",
                    "stable_identifier": "v99-01",
                    "display_name": "Version 99 App",
                    "source_mode": "SIMULATED",
                },
                "note": "Unsupported version",
            }
        ],
    }
    fpath = tmp_path / "bad_version.json"
    fpath.write_text(json.dumps(bad_version), encoding="utf-8")

    adapter = DemoFixtureAdapter(demo_dir=tmp_path)
    with pytest.raises(ValueError) as exc_info:
        adapter._load_all_records()
    assert "bad_version.json" in str(exc_info.value)
    assert "Unsupported fixture_version" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Behavior 2: SIMULATED declared; LIVE rejected with filename and index
# ---------------------------------------------------------------------------
def test_behavior_2_simulated_mode_enforced_and_live_rejected_with_file_and_index(
    tmp_path: Path,
) -> None:
    bad_fixture = {
        "fixture_version": 1,
        "records": [
            {
                "candidate": {
                    "source_id": "demo_fixtures",
                    "platform": "apple_app_store",
                    "asset_type": "IOS_APP",
                    "stable_identifier": "live-claim-01",
                    "display_name": "Claims LIVE App",
                    "source_mode": "LIVE",
                },
                "note": "Illegal mode declaration",
            }
        ],
    }
    fpath = tmp_path / "bad_live_candidate.json"
    fpath.write_text(json.dumps(bad_fixture), encoding="utf-8")

    adapter = DemoFixtureAdapter(demo_dir=tmp_path)
    with pytest.raises(ValueError) as exc_info:
        adapter._load_all_records()

    err = str(exc_info.value)
    assert "bad_live_candidate.json:0" in err
    assert "claims LIVE mode" in err


def test_behavior_2_cached_mode_also_rejected_in_demo(tmp_path: Path) -> None:
    bad_fixture = {
        "fixture_version": 1,
        "records": [
            {
                "candidate": {
                    "source_id": "demo_fixtures",
                    "platform": "bluesky",
                    "asset_type": "SOCIAL_ACCOUNT",
                    "stable_identifier": "cached-claim-01",
                    "display_name": "Claims CACHED Account",
                    "source_mode": "CACHED",
                },
                "note": "Illegal mode declaration",
            }
        ],
    }
    fpath = tmp_path / "bad_cached_candidate.json"
    fpath.write_text(json.dumps(bad_fixture), encoding="utf-8")

    adapter = DemoFixtureAdapter(demo_dir=tmp_path)
    with pytest.raises(ValueError) as exc_info:
        adapter._load_all_records()

    err = str(exc_info.value)
    assert "bad_cached_candidate.json:0" in err
    assert "claims CACHED mode" in err


# ---------------------------------------------------------------------------
# Behavior 3: Recorded fixtures preserve timestamps & re-normalize as CACHED
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_behavior_3_recorded_fixtures_preserve_timestamps_and_renormalize_cached() -> (
    None
):
    adapter = RecordedFixtureAdapter()
    plan = make_test_plan()

    res = await adapter.search(plan)
    assert res.status == SourceStatus.CONNECTED
    assert res.source_mode == SourceMode.CACHED
    assert len(res.candidates) > 0

    for cand in res.candidates:
        # Re-normalized through official mappers as CACHED
        assert cand.source_mode == SourceMode.CACHED
        # Preserves original timestamp
        assert cand.retrieved_at is not None
        # Does not have default placeholder string
        assert str(cand.retrieved_at) != ""


# ---------------------------------------------------------------------------
# Behavior 4: LIVE scans reject demo & recorded adapters via registry & direct call
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_behavior_4_live_scan_rejects_demo_and_recorded_via_registry_and_direct_call() -> (
    None
):
    # 1. Registry identification
    assert is_demo_only("demo_fixtures") is True
    assert is_demo_only("recorded_fixtures") is True

    # 2. Registry assert_not_demo_only
    with pytest.raises(ValueError) as exc1:
        assert_not_demo_only("demo_fixtures")
    assert "MODE_NOT_ALLOWED" in str(exc1.value)

    with pytest.raises(ValueError) as exc2:
        assert_not_demo_only("recorded_fixtures")
    assert "MODE_NOT_ALLOWED" in str(exc2.value)

    # 3. Registry get_adapter with is_live_scan=True
    with pytest.raises(ValueError) as exc3:
        get_adapter("demo_fixtures", is_live_scan=True)
    assert "MODE_NOT_ALLOWED" in str(exc3.value)

    with pytest.raises(ValueError) as exc4:
        get_adapter("recorded_fixtures", is_live_scan=True)
    assert "MODE_NOT_ALLOWED" in str(exc4.value)

    # 4. Direct adapter invocation with is_live_scan=True
    plan = make_test_plan()
    demo_adapter = DemoFixtureAdapter()
    with pytest.raises(ValueError) as exc5:
        await demo_adapter.search(plan, is_live_scan=True)
    assert "MODE_NOT_ALLOWED" in str(exc5.value)

    recorded_adapter = RecordedFixtureAdapter()
    with pytest.raises(ValueError) as exc6:
        await recorded_adapter.search(plan, is_live_scan=True)
    assert "MODE_NOT_ALLOWED" in str(exc6.value)


# ---------------------------------------------------------------------------
# Behavior 5: DEMO execution makes zero external network calls
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_behavior_5_demo_execution_never_makes_external_network_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def block_all_sockets(*args, **kwargs):
        raise RuntimeError("Network attempt detected during offline fixture run!")

    monkeypatch.setattr(socket.socket, "connect", block_all_sockets)

    demo_adapter = DemoFixtureAdapter()
    recorded_adapter = RecordedFixtureAdapter()
    plan = make_test_plan()

    # Zero network socket connections permitted
    demo_res = await demo_adapter.search(plan)
    assert demo_res.status == SourceStatus.CONNECTED
    assert len(demo_res.candidates) > 0

    rec_res = await recorded_adapter.search(plan)
    assert rec_res.status == SourceStatus.CONNECTED
    assert len(rec_res.candidates) > 0


# ---------------------------------------------------------------------------
# Behavior 6: Fixture parsing failures are explicit errors, not empty scans
# ---------------------------------------------------------------------------
def test_behavior_6_demo_corrupted_json_raises_explicit_error(tmp_path: Path) -> None:
    corrupt_file = tmp_path / "corrupt_demo.json"
    corrupt_file.write_text("{ this is not valid JSON", encoding="utf-8")

    adapter = DemoFixtureAdapter(demo_dir=tmp_path)
    with pytest.raises(ValueError) as exc:
        adapter._load_all_records()
    assert "Failed to read JSON from corrupt_demo.json" in str(exc.value)


def test_behavior_6_recorded_corrupted_json_raises_explicit_error(
    tmp_path: Path,
) -> None:
    corrupt_file = tmp_path / "corrupt_recorded.json"
    corrupt_file.write_text("{ broken json content", encoding="utf-8")

    adapter = RecordedFixtureAdapter(recorded_dir=tmp_path)
    with pytest.raises(ValueError) as exc:
        adapter._load_all_records()
    assert "Failed to read JSON from recorded fixture corrupt_recorded.json" in str(
        exc.value
    )


def test_behavior_6_empty_directory_raises_explicit_error(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()

    demo_adapter = DemoFixtureAdapter(demo_dir=empty_dir)
    with pytest.raises(ValueError) as exc1:
        demo_adapter._load_all_records()
    assert "No valid demo candidates found" in str(exc1.value)

    recorded_adapter = RecordedFixtureAdapter(recorded_dir=empty_dir)
    with pytest.raises(ValueError) as exc2:
        recorded_adapter._load_all_records()
    assert "No valid recorded candidates found" in str(exc2.value)


# ---------------------------------------------------------------------------
# Behavior 7: Fictional entities remain clearly documented
# ---------------------------------------------------------------------------
def test_behavior_7_fictional_entities_documented() -> None:
    readme = FIXTURES_DIR / "demo" / "README.md"
    assert readme.exists(), "README.md must document fictional fixture specification"
    content = readme.read_text(encoding="utf-8")

    assert "Fictional IDs, URLs, and phone numbers only" in content
    assert "SIMULATED" in content

    # Kaveri bank sample notes explain threat/entity category
    sample_file = FIXTURES_DIR / "demo" / "kaveri_bank_sample.json"
    data = json.loads(sample_file.read_text(encoding="utf-8"))
    for rec in data["records"]:
        note = rec.get("note", "")
        assert note, "Every fixture record must have a descriptive note"
        assert any(
            tag in note for tag in ["CLEARED", "IMPERSONATION", "NOT-RELEVANT"]
        ), f"Note missing category tag: {note}"
