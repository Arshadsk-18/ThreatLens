"""Deployment Smoke and Readiness Tests for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 21
"""

from datetime import datetime, timezone
from unittest.mock import patch

from starlette.testclient import TestClient

from app.core.config import settings
from app.core.prefill_service import register_source_adapter
from app.schemas.candidate import NormalizedCandidate, QueryPlan, SourceResult
from app.schemas.enums import AssetType, ScanStatus, SourceMode, SourceStatus
from app.schemas.source import SourceHealth


class MockLiveAppleAdapter:
    """Mock live adapter for smoke testing."""

    source_id = "apple_itunes"

    async def health_check(self) -> SourceHealth:
        return SourceHealth(
            source_id=self.source_id,
            status=SourceStatus.CONNECTED,
            latency_ms=15,
        )

    async def search(
        self,
        plan: QueryPlan,
        limit: int,
        *,
        force_refresh: bool,
        allow_stale_cache: bool,
    ) -> SourceResult:
        now = datetime.now(timezone.utc)
        candidates = [
            NormalizedCandidate(
                source_id=self.source_id,
                platform="apple_app_store",
                asset_type=AssetType.IOS_APP,
                stable_identifier="apple_live_12345",
                display_name="Kaveri Bank Official",
                developer_id="9000000001",
                source_mode=SourceMode.LIVE,
                retrieved_at=now,
            ),
            NormalizedCandidate(
                source_id=self.source_id,
                platform="apple_app_store",
                asset_type=AssetType.IOS_APP,
                stable_identifier="apple_live_99999",
                display_name="Kaveri Bank Rewards",
                developer_id="9000000042",
                category="Finance",
                source_mode=SourceMode.LIVE,
                retrieved_at=now,
            ),
        ]
        return SourceResult(
            source_id=self.source_id,
            status=SourceStatus.CONNECTED,
            source_mode=SourceMode.LIVE,
            queries_executed=len(plan.queries),
            candidates=candidates[:limit],
            cache_hit_count=0,
            duration_ms=45,
            retrieved_at=now,
        )

    async def lookup(self, identifier: str) -> NormalizedCandidate | None:
        return None


def _wait_for_scan(client: TestClient, scan_id: str) -> dict:
    for _ in range(30):
        res = client.get(f"/api/v1/scans/{scan_id}")
        data = res.json()
        if data["status"] in {"COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"}:
            return data
    raise TimeoutError("Scan timed out in smoke test")


def test_deploy_health_endpoint(client: TestClient) -> None:
    """GET /api/v1/health must return 200 with status ok and contract versions."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "threatlens-api"
    assert data["version"] == "3.0.0"
    assert data["contract_version"] == "3.0.0"


def test_deploy_ready_endpoint_no_secrets(client: TestClient) -> None:
    """GET /api/v1/ready must return subsystem status without exposing credentials."""
    res = client.get("/api/v1/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["ready"] is True
    assert "checks" in data
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["config"] == "ok"

    # Strict secret leakage check
    body_str = res.text.lower()
    for secret_word in ["password", "secret", "postgres:", "supabase.com", "token"]:
        assert secret_word not in body_str, f"Leaked potential credential '{secret_word}' in /ready"


def test_deploy_meta_endpoint(client: TestClient) -> None:
    """GET /api/v1/meta must return full enum catalog, scoring thresholds, and supported platforms."""
    res = client.get("/api/v1/meta")
    assert res.status_code == 200
    data = res.json()
    assert data["contract_version"] == "3.0.0"
    assert "enums" in data
    assert "thresholds" in data
    assert "supported_platforms" in data
    assert any(p["platform"] == "apple_app_store" for p in data["supported_platforms"])


def test_deploy_sources_status(client: TestClient) -> None:
    """GET /api/v1/sources/status must list 9 fixed sources with unconnected platforms explicitly marked."""
    res = client.get("/api/v1/sources/status?refresh=false")
    assert res.status_code == 200
    sources = res.json()
    assert isinstance(sources, list)
    assert len(sources) == 9

    status_by_id = {s["source_id"]: s["status"] for s in sources}
    assert status_by_id["google_play_snapshot"] == "NOT_CONNECTED"
    assert status_by_id["instagram"] == "NOT_CONNECTED"
    assert status_by_id["x"] == "NOT_CONNECTED"
    assert status_by_id["facebook"] == "NOT_CONNECTED"


def test_deploy_demo_scan_makes_no_provider_calls(client: TestClient) -> None:
    """DEMO scans must execute offline using local fixture doubles with zero network calls."""
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank", "industry_category": "Finance"}).json()
    b_id = brand["id"]

    with patch("httpx.AsyncClient.get", side_effect=RuntimeError("Network call blocked during DEMO scan!")), \
         patch("httpx.AsyncClient.post", side_effect=RuntimeError("Network call blocked during DEMO scan!")):
        start = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "DEMO", "source_ids": ["demo_fixtures"]})
        assert start.status_code == 202
        scan = _wait_for_scan(client, start.json()["id"])
        assert scan["status"] == "COMPLETED"

    # Verify all DEMO findings are honestly labeled SIMULATED
    findings_res = client.get(f"/api/v1/scans/{scan['id']}/findings")
    assert findings_res.status_code == 200
    findings = findings_res.json()["items"]
    for f in findings:
        assert f["source_mode"] == "SIMULATED"


def test_deploy_live_apple_scan_funnel_and_timestamps(client: TestClient) -> None:
    """LIVE Apple scan must execute with honest timestamps, LIVE source modes, and uphold funnel invariant."""
    brand = client.post("/api/v1/brands", json={"name": "Kaveri Bank", "industry_category": "Finance"}).json()
    b_id = brand["id"]

    # Register official app with numeric stable_identifier
    reg_res = client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "IOS_APP",
            "platform": "apple_app_store",
            "stable_identifier": "1234500001",
            "developer_id": "9000000001",
            "display_name": "Kaveri Bank Official",
            "is_verified": True,
        },
    )
    assert reg_res.status_code == 201

    class LiveAdapterWithNumericID(MockLiveAppleAdapter):
        async def search(self, plan, limit, *, force_refresh, allow_stale_cache):
            now = datetime.now(timezone.utc)
            candidates = [
                NormalizedCandidate(
                    source_id=self.source_id,
                    platform="apple_app_store",
                    asset_type=AssetType.IOS_APP,
                    stable_identifier="1234500001",
                    display_name="Kaveri Bank Official",
                    developer_id="9000000001",
                    source_mode=SourceMode.LIVE,
                    retrieved_at=now,
                ),
                NormalizedCandidate(
                    source_id=self.source_id,
                    platform="apple_app_store",
                    asset_type=AssetType.IOS_APP,
                    stable_identifier="9999900002",
                    display_name="Kaveri Bank Rewards",
                    developer_id="9000000042",
                    category="Finance",
                    source_mode=SourceMode.LIVE,
                    retrieved_at=now,
                ),
            ]
            return SourceResult(
                source_id=self.source_id,
                status=SourceStatus.CONNECTED,
                source_mode=SourceMode.LIVE,
                queries_executed=len(plan.queries),
                candidates=candidates[:limit],
                cache_hit_count=0,
                duration_ms=45,
                retrieved_at=now,
            )

    register_source_adapter("apple_itunes", LiveAdapterWithNumericID())

    start = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]})
    assert start.status_code == 202
    scan = _wait_for_scan(client, start.json()["id"])
    assert scan["status"] == "COMPLETED"

    funnel = scan["funnel"]
    assert funnel["retrieved"] == 2
    assert funnel["deduplicated"] == 2
    assert funnel["official_cleared"] == 1
    assert funnel["findings"] == 1
    # Funnel invariant
    assert funnel["deduplicated"] == (
        funnel["official_cleared"]
        + funnel["not_relevant"]
        + funnel["benign_lookalike"]
        + funnel["below_threshold"]
        + funnel["findings"]
    )

    # Check timestamps and source modes in findings
    findings = client.get(f"/api/v1/scans/{scan['id']}/findings").json()["items"]
    assert len(findings) == 1
    assert findings[0]["source_mode"] == "LIVE"
    assert findings[0]["observed_at"] is not None


def test_deploy_cors_exact_origin_and_preflight(client: TestClient) -> None:
    """CORS middleware must allow registered frontend origin and reject wildcard in production."""
    # Test preflight OPTIONS request
    origin = settings.CORS_ORIGINS[0]
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type, X-Request-ID",
    }
    res = client.options("/api/v1/scans", headers=headers)
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == origin
    assert "*" not in settings.CORS_ORIGINS, "CORS_ORIGINS must not contain wildcard in production deployment"


def test_deploy_restart_safety_scan_interruption_recovery(client: TestClient) -> None:
    """Any scan left in RUNNING status must be set to FAILED with exact contract interruption message."""
    from app.core.memory_store import get_memory_store

    store = get_memory_store()
    brand = client.post("/api/v1/brands", json={"name": "CrashRecoveryBrand", "industry_category": "Banking"}).json()

    # Manually inject an interrupted scan
    interrupted_scan_id = client.post(
        "/api/v1/scans",
        json={"brand_id": brand["id"], "mode": "LIVE", "source_ids": ["google_play_snapshot"]},
    ).json()["id"]

    # Simulate crash leaving scan in RUNNING
    from uuid import UUID
    store.scans[UUID(interrupted_scan_id)]["status"] = ScanStatus.RUNNING

    # Run startup recovery hook
    recovered_count = store.recover_running_scans()
    assert recovered_count >= 1

    # Verify scan status and exact error message
    scan_detail = client.get(f"/api/v1/scans/{interrupted_scan_id}").json()
    assert scan_detail["status"] == "FAILED"
    assert scan_detail["error_message"] == "Interrupted by server restart"
