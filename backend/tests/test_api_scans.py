"""Integration tests for P0 scan routes and orchestrator.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 5.2, 5.3, 5.5, 11.4
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.memory_store import get_memory_store
from app.core.prefill_service import register_source_adapter
from app.schemas.candidate import NormalizedCandidate, QueryPlan, SourceResult
from app.schemas.enums import (
    ApiErrorCode,
    AssetType,
    ScanMode,
    ScanStatus,
    SourceMode,
    SourceStatus,
)
from app.schemas.source import SourceHealth
from app.services.sources.base import SourceAdapter


@pytest.fixture(autouse=True)
def clean_store():
    """Reset store before and after each test."""
    store = get_memory_store()
    store.clear()
    yield
    store.clear()


class FakeAppleAdapter(SourceAdapter):
    """Fake Apple iTunes adapter for walking skeleton integration tests."""

    source_id = "apple_itunes"

    def __init__(
        self,
        candidates: list[NormalizedCandidate] | None = None,
        status: SourceStatus = SourceStatus.CONNECTED,
        block: bool = False,
    ):
        self._candidates = candidates if candidates is not None else []
        self._status = status
        self.is_blocked = block


    async def health_check(self) -> SourceHealth:
        return SourceHealth(
            source_id="apple_itunes",
            display_name="Apple App Store search",
            platform="apple_app_store",
            status=self._status,
            supported_modes=[SourceMode.LIVE, SourceMode.CACHED],
            default_mode=SourceMode.LIVE,
        )

    async def search(
        self,
        plan: QueryPlan,
        limit: int,
        *,
        force_refresh: bool,
        allow_stale_cache: bool,
    ) -> SourceResult:
        while self.is_blocked:
            await asyncio.sleep(0)

        return SourceResult(
            source_id="apple_itunes",
            status=self._status,
            source_mode=SourceMode.LIVE,
            candidates=self._candidates,
            queries_executed=len(plan.queries),
            cache_hit_count=0,
            error_code=None if self._status == SourceStatus.CONNECTED else "PROVIDER_UNAVAILABLE",
            message="Queries executed." if self._status == SourceStatus.CONNECTED else "Provider failed.",
            duration_ms=25,
        )

    async def lookup(self, identifier: str):
        for c in self._candidates:
            if c.stable_identifier == identifier:
                return c
        return None


def wait_for_scan(client: TestClient, scan_id: str, timeout: float = 3.0) -> dict:
    """Helper to poll scan detail until terminal status."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = client.get(f"/api/v1/scans/{scan_id}")
        assert res.status_code == 200
        data = res.json()
        if data["status"] in {"COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"}:
            return data
        time.sleep(0.02)
    raise TimeoutError(f"Scan {scan_id} did not complete within {timeout}s")


def test_start_scan_success(client: TestClient) -> None:
    """POST /api/v1/scans queues a scan job and returns 202."""
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = brand["id"]

    payload = {
        "brand_id": b_id,
        "mode": "LIVE",
        "asset_types": ["IOS_APP"],
        "source_ids": ["apple_itunes"],
        "query_limit_per_source": 25,
    }
    res = client.post("/api/v1/scans", json=payload)
    assert res.status_code == 202

    data = res.json()
    assert data["brand_id"] == b_id
    assert data["mode"] == "LIVE"
    assert data["status"] == "QUEUED"
    assert data["stage"] == "queued"
    assert data["progress_percent"] == 0
    assert "id" in data


def test_concurrent_scan_blocked_by_409(client: TestClient) -> None:
    """Enforce one running scan per brand constraint (409 SCAN_ALREADY_RUNNING)."""
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = brand["id"]

    # Register an adapter with block=True so the scan remains in RUNNING
    slow_adapter = FakeAppleAdapter(candidates=[], block=True)
    register_source_adapter("apple_itunes", slow_adapter)

    # Queue first scan
    r1 = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]})
    assert r1.status_code == 202
    scan_1_id = r1.json()["id"]

    # Queue second scan immediately on same brand while first is in-flight
    r2 = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]})
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == ApiErrorCode.SCAN_ALREADY_RUNNING.value

    # Unblock adapter and wait for first scan to complete
    slow_adapter.is_blocked = False
    wait_for_scan(client, scan_1_id)

    # Now a new scan on the brand can be queued successfully
    r3 = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]})
    assert r3.status_code == 202




def test_mode_not_allowed_for_live_demo_fixtures(client: TestClient) -> None:
    """LIVE scan with demo_fixtures returns 422 MODE_NOT_ALLOWED."""
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = brand["id"]

    payload = {
        "brand_id": b_id,
        "mode": "LIVE",
        "source_ids": ["demo_fixtures"],
    }
    res = client.post("/api/v1/scans", json=payload)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == ApiErrorCode.MODE_NOT_ALLOWED.value


def test_walking_skeleton_live_apple_scan_funnel_and_findings(client: TestClient) -> None:
    """Milestone M2 Walking Skeleton:

    Live Apple scan -> normalized candidates -> assess stub -> persistence -> findings/cleared endpoints.
    Enforces exact Funnel Invariant:
    deduplicated == official_cleared + not_relevant + benign_lookalike + below_threshold + findings
    and retrieved >= deduplicated.
    """
    # 1. Setup brand and official assets
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank", "industry_category": "Finance"}).json()
    b_id = brand["id"]

    # Register official app 1234567890 (verified)
    client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "IOS_APP",
            "platform": "apple_app_store",
            "stable_identifier": "1234567890",
            "developer_id": "9000000001",
            "display_name": "Kaveri Bank",
            "is_verified": True,
            "trust_publisher": True,
        },
    )

    # 2. Register fake Apple adapter with diverse test candidates:
    # - c1: Exact match official app (should land in official_cleared)
    # - c2: Duplicate copy of c1 (should be deduplicated)
    # - c3: Second app by registered developer ID (official_cleared via R2)
    # - c4: Unrelated category candidate "Kaveri Coffee" (benign_lookalike via G4)
    # - c5: Candidate below threshold (below_threshold)
    # - c6: Completely irrelevant candidate (not_relevant via G1)
    # - c7: Impersonating lookalike "Kaveri Bank Rewards" (findings)
    now = datetime.now(timezone.utc)
    candidates = [
        # c1
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="1234567890",
            display_name="Kaveri Bank",
            developer_id="9000000001",
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
        # c2 (duplicate of c1)
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="1234567890",
            display_name="Kaveri Bank",
            developer_id="9000000001",
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
        # c3 (publisher ID match)
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="1111222233",
            display_name="Kaveri Wealth",
            developer_id="9000000001",
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
        # c4 (benign lookalike: coffee roasters)
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="4444555566",
            display_name="Kaveri Coffee Roasters",
            category="Food & Drink",
            developer_id="9999999999",
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
        # c5 (below threshold)
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="below_threshold_app",
            display_name="Kaveri Local Guide",
            developer_id="8888888888",
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
        # c6 (irrelevant)
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="irrelevant_unrelated_app",
            display_name="Completely Random Game",
            developer_id="7777777777",
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
        # c7 (candidate for review finding)
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="9876543210",
            display_name="Kaveri Bank Rewards",
            publisher_name="KB Rewards Studio",
            developer_id="9000000042",
            category="Finance",
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
    ]

    adapter = FakeAppleAdapter(candidates=candidates)
    register_source_adapter("apple_itunes", adapter)

    # 3. Start scan
    start_res = client.post(
        "/api/v1/scans",
        json={
            "brand_id": b_id,
            "mode": "LIVE",
            "source_ids": ["apple_itunes"],
        },
    )
    assert start_res.status_code == 202
    scan_id = start_res.json()["id"]

    # 4. Poll until completed
    scan_data = wait_for_scan(client, scan_id)
    assert scan_data["status"] == "COMPLETED"
    assert scan_data["progress_percent"] == 100

    # 5. Verify Funnel Invariant
    funnel = scan_data["funnel"]
    assert funnel["retrieved"] == 7
    assert funnel["deduplicated"] == 6
    assert funnel["official_cleared"] == 2  # c1 (exact ID) + c3 (developer ID)
    assert funnel["benign_lookalike"] == 1  # c4 (coffee roasters)
    assert funnel["below_threshold"] == 1   # c5
    assert funnel["not_relevant"] == 1      # c6
    assert funnel["findings"] == 1          # c7

    # INVARIANT CHECK:
    assert funnel["deduplicated"] == (
        funnel["official_cleared"]
        + funnel["not_relevant"]
        + funnel["benign_lookalike"]
        + funnel["below_threshold"]
        + funnel["findings"]
    )
    assert funnel["retrieved"] >= funnel["deduplicated"]

    # 6. Verify GET /scans/{scan_id}/findings
    findings_res = client.get(f"/api/v1/scans/{scan_id}/findings")
    assert findings_res.status_code == 200
    findings_data = findings_res.json()
    assert findings_data["total"] == 1
    finding_item = findings_data["items"][0]
    assert finding_item["candidate"]["display_name"] == "Kaveri Bank Rewards"
    assert finding_item["risk_score"] == 72
    assert finding_item["severity"] == "HIGH"
    assert finding_item["source_mode"] == "LIVE"

    # 7. Verify GET /scans/{scan_id}/cleared
    cleared_res = client.get(f"/api/v1/scans/{scan_id}/cleared")
    assert cleared_res.status_code == 200
    cleared_data = cleared_res.json()
    # 2 official cleared + 1 benign lookalike + 1 below threshold = 4 cleared items
    assert cleared_data["total"] == 4
    decisions = {item["decision"] for item in cleared_data["items"]}
    assert "OFFICIAL_EXACT_MATCH" in decisions
    assert "OFFICIAL_PUBLISHER_MATCH" in decisions
    assert "BENIGN_LOOKALIKE" in decisions
    assert "BELOW_THRESHOLD" in decisions


def test_provider_failure_is_not_clean_scan(client: TestClient) -> None:
    """A provider failure with zero candidates must be visible as ERROR/COMPLETED_WITH_ERRORS, not clean 0-result."""
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = brand["id"]

    # Adapter that fails
    adapter = FakeAppleAdapter(candidates=[], status=SourceStatus.ERROR)
    register_source_adapter("apple_itunes", adapter)

    res = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]})
    scan_id = res.json()["id"]

    detail = wait_for_scan(client, scan_id)
    assert detail["status"] == "COMPLETED_WITH_ERRORS"
    assert len(detail["source_outcomes"]) == 1
    outcome = detail["source_outcomes"][0]
    assert outcome["status"] == "ERROR"
    assert outcome["error_code"] == "PROVIDER_UNAVAILABLE"


def test_not_connected_source_does_not_cause_scan_error(client: TestClient) -> None:
    """NOT_CONNECTED sources (e.g. google_play_snapshot in LIVE) do not make scan COMPLETED_WITH_ERRORS."""
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = brand["id"]

    # Apple succeeds, google_play is not connected
    adapter = FakeAppleAdapter(candidates=[], status=SourceStatus.CONNECTED)
    register_source_adapter("apple_itunes", adapter)

    res = client.post(
        "/api/v1/scans",
        json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes", "google_play_snapshot"]},
    )
    scan_id = res.json()["id"]

    detail = wait_for_scan(client, scan_id)
    assert detail["status"] == "COMPLETED"
    statuses = {o["source_id"]: o["status"] for o in detail["source_outcomes"]}
    assert statuses["apple_itunes"] == "CONNECTED"
    assert statuses["google_play_snapshot"] == "NOT_CONNECTED"


def test_server_restart_scan_recovery(client: TestClient) -> None:
    """RUNNING or QUEUED scans left by server restart become FAILED with contract interruption message."""
    store = get_memory_store()
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = uuid.UUID(brand["id"])

    # Simulate scan left in RUNNING
    from app.schemas.scan import ScanOptions
    scan_res = store.create_scan(b_id, ScanMode.LIVE, ScanOptions())
    scan_id = scan_res.id

    store.update_scan_progress(scan_id, "fetching", 30, status=ScanStatus.RUNNING)

    # Perform restart recovery
    recovered_count = store.recover_running_scans()
    assert recovered_count == 1

    detail = client.get(f"/api/v1/scans/{scan_id}").json()
    assert detail["status"] == "FAILED"
    assert detail["stage"] == "failed"
    assert detail["error_message"] == "Interrupted by server restart"

    # Concurrency lock is released so brand can be scanned again
    new_res = client.post("/api/v1/scans", json={"brand_id": str(b_id), "mode": "LIVE"})
    assert new_res.status_code == 202


def test_empty_scan_funnel_invariant(client: TestClient) -> None:
    """When a source returns 0 candidates, funnel invariant holds exactly with all zeros."""
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = brand["id"]

    adapter = FakeAppleAdapter(candidates=[], status=SourceStatus.CONNECTED)
    register_source_adapter("apple_itunes", adapter)

    res = client.post(
        "/api/v1/scans",
        json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]},
    )
    scan_id = res.json()["id"]
    detail = wait_for_scan(client, scan_id)

    assert detail["status"] == "COMPLETED"
    funnel = detail["funnel"]
    assert funnel["retrieved"] == 0
    assert funnel["deduplicated"] == 0
    assert funnel["official_cleared"] == 0
    assert funnel["not_relevant"] == 0
    assert funnel["benign_lookalike"] == 0
    assert funnel["below_threshold"] == 0
    assert funnel["findings"] == 0
    assert funnel["deduplicated"] == (
        funnel["official_cleared"]
        + funnel["not_relevant"]
        + funnel["benign_lookalike"]
        + funnel["below_threshold"]
        + funnel["findings"]
    )


def test_demo_mode_uses_local_fixture_double(client: TestClient) -> None:
    """DEMO mode uses local fixture adapters and produces simulated candidates."""
    # Reset any registered adapter so DEMO fallback fixture runs
    from app.core.prefill_service import _adapters
    _adapters.pop("apple_itunes", None)

    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = brand["id"]

    res = client.post(
        "/api/v1/scans",
        json={"brand_id": b_id, "mode": "DEMO", "source_ids": ["apple_itunes"]},
    )
    assert res.status_code == 202
    scan_id = res.json()["id"]

    detail = wait_for_scan(client, scan_id)
    assert detail["status"] == "COMPLETED"
    assert detail["mode"] == "DEMO"
    assert detail["funnel"]["retrieved"] > 0


def test_live_scan_rejects_simulated_records(client: TestClient) -> None:
    """LIVE scans strictly reject SIMULATED records with ModeNotAllowedException/FAILED."""
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = brand["id"]

    now = datetime.now(timezone.utc)
    simulated_cand = NormalizedCandidate(
        source_id="apple_itunes",
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier="sim_123",
        display_name="Kaveri Bank Phish",
        source_mode=SourceMode.SIMULATED,  # Invalid in LIVE
        retrieved_at=now,
    )
    adapter = FakeAppleAdapter(candidates=[simulated_cand], status=SourceStatus.CONNECTED)
    register_source_adapter("apple_itunes", adapter)

    res = client.post(
        "/api/v1/scans",
        json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]},
    )
    scan_id = res.json()["id"]
    detail = wait_for_scan(client, scan_id)
    assert detail["status"] == "FAILED"
    assert "MODE_NOT_ALLOWED" in (detail["error_message"] or "")


def test_scan_query_limit_validation(client: TestClient) -> None:
    """query_limit_per_source must be between 1 and 50 (contract default 25, max 50)."""
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = brand["id"]

    # Exceeding max 50
    res = client.post(
        "/api/v1/scans",
        json={"brand_id": b_id, "mode": "LIVE", "query_limit_per_source": 51},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == ApiErrorCode.VALIDATION_ERROR.value

    # Below min 1
    res2 = client.post(
        "/api/v1/scans",
        json={"brand_id": b_id, "mode": "LIVE", "query_limit_per_source": 0},
    )
    assert res2.status_code == 422


def test_list_scans_pagination(client: TestClient) -> None:
    """GET /api/v1/scans returns paginated scan records."""
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = brand["id"]

    res = client.get(f"/api/v1/scans?brand_id={b_id}")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


def test_demo_scan_strictly_zero_network_and_live_adapters_uncalled(client: TestClient) -> None:
    """DEMO scans must make zero network requests, never invoke live adapters, and produce SIMULATED records fulfilling funnel invariant."""
    from unittest.mock import patch

    from app.core.prefill_service import register_source_adapter
    from app.schemas.candidate import QueryPlan, SourceResult

    class ExplosiveLiveAdapter:
        source_id = "apple_itunes"
        called = False

        async def search(self, plan: QueryPlan, limit: int, **kwargs) -> SourceResult:
            ExplosiveLiveAdapter.called = True
            raise AssertionError("CRITICAL VIOLATION: Live adapter called during DEMO scan!")

        async def health_check(self):
            pass

        async def lookup(self, identifier: str):
            return None

    explosive = ExplosiveLiveAdapter()
    register_source_adapter("apple_itunes", explosive)

    brand = client.post(
        "/api/v1/brands",
        json={"name": "Kaveri Bank", "industry_category": "Finance"},
    ).json()
    b_id = brand["id"]

    # Block socket and HTTP entry points completely
    with patch("socket.socket.connect", side_effect=AssertionError("Socket connect attempted in DEMO scan!")), \
         patch("httpx.AsyncClient.request", side_effect=AssertionError("httpx request attempted in DEMO scan!")), \
         patch("httpx.AsyncClient.get", side_effect=AssertionError("httpx GET attempted in DEMO scan!")), \
         patch("httpx.AsyncClient.post", side_effect=AssertionError("httpx POST attempted in DEMO scan!")):

        # Request DEMO scan with live source IDs passed (contract: DEMO ignores live source_ids)
        res = client.post(
            "/api/v1/scans",
            json={"brand_id": b_id, "mode": "DEMO", "source_ids": ["apple_itunes", "bluesky_public"]},
        )
        assert res.status_code == 202
        scan_id = res.json()["id"]

        detail = wait_for_scan(client, scan_id)
        assert detail["status"] == "COMPLETED"
        assert detail["mode"] == "DEMO"

    # 1. Live adapter was NEVER invoked
    assert explosive.called is False, "Live adapter was invoked during DEMO scan execution!"

    # 2. Funnel invariant holds
    funnel = detail["funnel"]
    assert funnel["retrieved"] > 0
    assert funnel["retrieved"] >= funnel["deduplicated"]
    assert funnel["deduplicated"] == (
        funnel["official_cleared"]
        + funnel["not_relevant"]
        + funnel["benign_lookalike"]
        + funnel["below_threshold"]
        + funnel["findings"]
    )

    # 3. All findings and cleared items are honestly SIMULATED
    findings = client.get(f"/api/v1/scans/{scan_id}/findings").json()["items"]
    for f in findings:
        assert f["source_mode"] == "SIMULATED"

    cleared = client.get(f"/api/v1/scans/{scan_id}/cleared").json()["items"]
    for c in cleared:
        assert c["source_mode"] == "SIMULATED"


def test_demo_scan_missing_fixture_causes_explicit_error_and_never_calls_live(client: TestClient) -> None:
    """Missing or corrupted fixtures must cause an explicit error and NEVER fall back to live adapters."""
    from unittest.mock import patch

    from app.core.demo_fixtures import FixtureUnavailableError
    from app.core.prefill_service import register_source_adapter
    from app.schemas.candidate import QueryPlan, SourceResult

    class ExplosiveLiveAdapter:
        source_id = "apple_itunes"
        called = False

        async def search(self, plan: QueryPlan, limit: int, **kwargs) -> SourceResult:
            ExplosiveLiveAdapter.called = True
            raise AssertionError("CRITICAL VIOLATION: Live adapter called when fixture was missing!")

        async def health_check(self):
            pass

        async def lookup(self, identifier: str):
            return None

    explosive = ExplosiveLiveAdapter()
    register_source_adapter("apple_itunes", explosive)

    brand = client.post("/api/v1/brands", json={"name": "Corrupted Bank"}).json()
    b_id = brand["id"]

    # Patch fixture loader to simulate corrupted fixture file
    with patch(
        "app.core.demo_fixtures.load_demo_fixture_candidates",
        side_effect=FixtureUnavailableError("Corrupted fixture json"),
    ):
        res = client.post(
            "/api/v1/scans",
            json={"brand_id": b_id, "mode": "DEMO", "source_ids": ["demo_fixtures"]},
        )
        assert res.status_code == 202
        scan_id = res.json()["id"]

        detail = wait_for_scan(client, scan_id)
        # Scan ends with error status because fixture failed
        assert detail["status"] == "COMPLETED_WITH_ERRORS"
        outcome = detail["source_outcomes"][0]
        assert outcome["status"] == "ERROR"
        assert outcome["error_code"] == "PROVIDER_UNAVAILABLE"
        assert "Demo fixture unavailable" in outcome["message"]

    # Live adapter was NEVER invoked as fallback
    assert explosive.called is False


def test_live_scan_rejects_recorded_fixtures_and_demo_fixtures(client: TestClient) -> None:
    """LIVE scans must reject demo_fixtures and recorded_fixtures with 422 MODE_NOT_ALLOWED."""
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = brand["id"]

    # 1. demo_fixtures in LIVE
    res1 = client.post(
        "/api/v1/scans",
        json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["demo_fixtures"]},
    )
    assert res1.status_code == 422
    assert res1.json()["error"]["code"] == ApiErrorCode.MODE_NOT_ALLOWED.value

    # 2. recorded_fixtures in LIVE
    res2 = client.post(
        "/api/v1/scans",
        json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["recorded_fixtures"]},
    )
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == ApiErrorCode.MODE_NOT_ALLOWED.value
