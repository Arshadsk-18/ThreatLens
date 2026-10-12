"""Unit and integration tests for Demo/Recorded fixture adapters, NotConnected, and Registry.

Owner: Person 3 (backend/app/services/sources/tests/test_registry_fixtures.py)
Reference: Contract Sections 5.3, 11.1, 12
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import respx

from app.schemas import (
    PlannedQuery,
    ProviderErrorCode,
    QueryPlan,
    SourceMode,
    SourceStatus,
)
from app.services.sources.apple import AppleItunesAdapter
from app.services.sources.bluesky import BlueskyPublicAdapter
from app.services.sources.fixtures_demo import DemoFixtureAdapter
from app.services.sources.fixtures_recorded import RecordedFixtureAdapter
from app.services.sources.not_connected import NotConnectedAdapter
from app.services.sources.registry import (
    FIXED_SOURCE_IDS,
    assert_not_demo_only,
    get_adapter,
    is_demo_only,
    source_catalog,
)

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "tests" / "fixtures"


def make_dummy_plan() -> QueryPlan:
    return QueryPlan(
        brand_id=uuid4(),
        queries=[
            PlannedQuery(term="kaveri bank", kind="BASE", priority=1),
            PlannedQuery(term="kaveri mobile", kind="SPACING", priority=2),
        ],
    )


@pytest.mark.asyncio
async def test_demo_scan_makes_no_network_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Socket-level guard test: proves Demo and Recorded adapters make ZERO network calls."""

    def block_socket_connect(*args, **kwargs):
        raise RuntimeError("Forbidden network socket connection attempted!")

    monkeypatch.setattr(socket.socket, "connect", block_socket_connect)

    demo_adapter = DemoFixtureAdapter()
    recorded_adapter = RecordedFixtureAdapter()
    plan = make_dummy_plan()

    # Demo search must succeed with zero network
    demo_res = await demo_adapter.search(plan, limit=50)
    assert demo_res.status == SourceStatus.CONNECTED
    assert demo_res.source_mode == SourceMode.SIMULATED
    assert len(demo_res.candidates) > 0
    assert all(c.source_mode == SourceMode.SIMULATED for c in demo_res.candidates)

    # Recorded search must succeed with zero network
    rec_res = await recorded_adapter.search(plan, limit=50)
    assert rec_res.status == SourceStatus.CONNECTED
    assert rec_res.source_mode == SourceMode.CACHED
    assert len(rec_res.candidates) > 0
    assert all(c.source_mode == SourceMode.CACHED for c in rec_res.candidates)


def test_wrong_source_mode_rejected(tmp_path: Path) -> None:
    """A record in a DEMO fixture claiming LIVE mode is rejected with a clear error."""
    bad_fixture = {
        "fixture_version": 1,
        "records": [
            {
                "candidate": {
                    "source_id": "demo_fixtures",
                    "platform": "apple_app_store",
                    "asset_type": "IOS_APP",
                    "stable_identifier": "bad-live-01",
                    "display_name": "Should not claim LIVE",
                    "source_mode": "LIVE",
                },
                "note": "Illegal mode",
            }
        ],
    }
    file_path = tmp_path / "bad_live.json"
    file_path.write_text(json.dumps(bad_fixture), encoding="utf-8")

    adapter = DemoFixtureAdapter(demo_dir=tmp_path)
    with pytest.raises(ValueError) as exc_info:
        adapter._load_all_records()

    err_msg = str(exc_info.value)
    assert "bad_live.json:0" in err_msg
    assert "claims LIVE mode" in err_msg


def test_invalid_record_reports_file_and_index(tmp_path: Path) -> None:
    """A malformed record raises ValueError detailing the filename and record index."""
    bad_fixture = {
        "fixture_version": 1,
        "records": [
            {
                "candidate": {
                    "source_id": "demo_fixtures",
                    # Missing platform, asset_type, stable_identifier, display_name
                },
                "note": "Missing required fields",
            }
        ],
    }
    file_path = tmp_path / "corrupt.json"
    file_path.write_text(json.dumps(bad_fixture), encoding="utf-8")

    adapter = DemoFixtureAdapter(demo_dir=tmp_path)
    with pytest.raises(ValueError) as exc_info:
        adapter._load_all_records()

    err_msg = str(exc_info.value)
    assert "corrupt.json:0" in err_msg


@pytest.mark.asyncio
async def test_not_connected_row_for_every_non_live_source_with_exact_messages() -> (
    None
):
    """Every non-live source reports NOT_CONNECTED with expected messages."""
    plan = make_dummy_plan()

    expected_checks = [
        ("google_play_snapshot", "No official API; not queried"),
        ("instagram", "Requires platform API access. Not queried."),
        ("x", "Requires platform API access. Not queried."),
        ("facebook", "Requires platform API access. Not queried."),
        ("bluesky_posts", "Post search not enabled in P0; not queried."),
    ]

    for sid, msg_part in expected_checks:
        adapter = get_adapter(sid)
        assert isinstance(adapter, NotConnectedAdapter)

        # 1. health_check
        health = await adapter.health_check()
        assert health.status == SourceStatus.NOT_CONNECTED
        assert health.source_id == sid
        assert msg_part in health.message

        # 2. search
        res = await adapter.search(plan)
        assert res.status == SourceStatus.NOT_CONNECTED
        assert res.source_mode is None
        assert res.candidates == []
        assert res.queries_executed == 0
        assert res.error_code is None
        assert msg_part in res.message


@pytest.mark.asyncio
async def test_not_connected_is_not_an_error() -> None:
    """NOT_CONNECTED status carries error_code=None and lookup returns None."""
    adapter = get_adapter("instagram")
    res = await adapter.search(make_dummy_plan())

    assert res.status == SourceStatus.NOT_CONNECTED
    assert res.error_code is None
    assert await adapter.lookup("test_account") is None


def test_catalog_contains_exactly_nine_ids_with_expected_default_states() -> None:
    """Registry source_catalog contains all 9 fixed source IDs in order."""
    catalog = source_catalog()
    assert len(catalog) == 9

    catalog_sids = [h.source_id for h in catalog]
    assert tuple(catalog_sids) == FIXED_SOURCE_IDS

    lookup_map = {h.source_id: h for h in catalog}

    # Live sources default to CONNECTED (initial session)
    assert lookup_map["apple_itunes"].status == SourceStatus.CONNECTED
    assert lookup_map["apple_itunes"].default_mode == SourceMode.LIVE
    assert lookup_map["bluesky_public"].status == SourceStatus.CONNECTED

    # Not connected sources
    assert lookup_map["bluesky_posts"].status == SourceStatus.NOT_CONNECTED
    assert lookup_map["google_play_snapshot"].status == SourceStatus.NOT_CONNECTED
    assert lookup_map["instagram"].status == SourceStatus.NOT_CONNECTED
    assert lookup_map["x"].status == SourceStatus.NOT_CONNECTED
    assert lookup_map["facebook"].status == SourceStatus.NOT_CONNECTED

    # Demo-only sources
    assert lookup_map["demo_fixtures"].status == SourceStatus.CONNECTED
    assert lookup_map["demo_fixtures"].supported_modes == [SourceMode.SIMULATED]
    assert lookup_map["recorded_fixtures"].status == SourceStatus.CONNECTED
    assert lookup_map["recorded_fixtures"].supported_modes == [SourceMode.CACHED]


def test_live_caller_cannot_obtain_demo_only_source() -> None:
    """Registry refuses to hand demo-only adapters to a LIVE scan context."""
    assert is_demo_only("demo_fixtures") is True
    assert is_demo_only("recorded_fixtures") is True
    assert is_demo_only("apple_itunes") is False
    assert is_demo_only("bluesky_public") is False

    # Raises when requested with is_live_scan=True
    with pytest.raises(ValueError) as exc1:
        get_adapter("demo_fixtures", is_live_scan=True)
    assert "MODE_NOT_ALLOWED" in str(exc1.value)

    with pytest.raises(ValueError) as exc2:
        get_adapter("recorded_fixtures", is_live_scan=True)
    assert "MODE_NOT_ALLOWED" in str(exc2.value)

    with pytest.raises(ValueError) as exc3:
        assert_not_demo_only("demo_fixtures")
    assert "MODE_NOT_ALLOWED" in str(exc3.value)


@pytest.mark.asyncio
@respx.mock
async def test_live_scan_has_no_simulated_records() -> None:
    """Live Apple and Bluesky adapters never produce SIMULATED records."""
    # Apple
    apple_adapter = AppleItunesAdapter()
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(200, json={"resultCount": 0, "results": []})
    )
    res_apple = await apple_adapter.search(make_dummy_plan(), limit=10)
    assert res_apple.source_mode != SourceMode.SIMULATED
    assert all(c.source_mode != SourceMode.SIMULATED for c in res_apple.candidates)

    # Bluesky
    bluesky_adapter = BlueskyPublicAdapter()
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(200, json={"actors": []})
    )
    res_bsky = await bluesky_adapter.search(make_dummy_plan(), limit=10)
    assert res_bsky.source_mode != SourceMode.SIMULATED
    assert all(c.source_mode != SourceMode.SIMULATED for c in res_bsky.candidates)


@pytest.mark.asyncio
@respx.mock
async def test_last_outcome_status_propagation_after_simulated_429() -> None:
    """After a simulated 429 rate limit on Apple adapter, catalog reflects RATE_LIMITED."""
    apple_adapter = get_adapter("apple_itunes")

    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(429, text="Too Many Requests")
    )

    plan = make_dummy_plan()
    res = await apple_adapter.search(plan, limit=5)
    assert res.status == SourceStatus.RATE_LIMITED
    assert res.error_code == ProviderErrorCode.RATE_LIMITED

    # Catalog and health check must propagate last real outcome
    health = await apple_adapter.health_check()
    assert health.status == SourceStatus.RATE_LIMITED

    catalog = source_catalog()
    apple_health = next(h for h in catalog if h.source_id == "apple_itunes")
    assert apple_health.status == SourceStatus.RATE_LIMITED
