"""Tests for Google Play Store snapshot source adapter and scan integration."""
import pytest
from app.schemas.candidate import PlannedQuery, QueryPlan
from app.schemas.enums import AssetType, SourceMode, SourceStatus
from app.services.sources.google_play import GooglePlaySnapshotAdapter
from starlette.testclient import TestClient


@pytest.mark.anyio
async def test_google_play_health_check():
    adapter = GooglePlaySnapshotAdapter()
    health = await adapter.health_check()
    assert health.status == SourceStatus.CONNECTED
    assert health.source_id == "google_play_snapshot"
    assert health.platform == "google_play"
    assert AssetType.ANDROID_APP in health.asset_types
    assert SourceMode.LIVE in health.supported_modes


@pytest.mark.anyio
async def test_google_play_search_generates_candidates():
    adapter = GooglePlaySnapshotAdapter()
    plan = QueryPlan(
        brand_id="00000000-0000-0000-0000-000000000001",
        queries=[PlannedQuery(term="Kaveri Bank", kind="BASE", priority=1)],
    )

    res = await adapter.search(plan, limit=10)
    assert res.status == SourceStatus.CONNECTED
    assert res.source_mode == SourceMode.LIVE
    assert len(res.candidates) >= 4
    assert len(res.candidates) <= 6

    for cand in res.candidates:
        assert cand.platform == "google_play"
        assert cand.asset_type == AssetType.ANDROID_APP
        assert cand.source_mode == SourceMode.LIVE
        assert "kaveri" in cand.display_name.lower()
        assert cand.stable_identifier.startswith("com.kaveribank.")
        assert "package_name" in cand.secondary_identifiers
        assert cand.canonical_url.startswith("https://play.google.com/store/apps/details?id=")


@pytest.mark.anyio
async def test_google_play_lookup():
    adapter = GooglePlaySnapshotAdapter()
    cand = await adapter.lookup("https://play.google.com/store/apps/details?id=com.kaveribank.mobile")
    assert cand is not None
    assert cand.platform == "google_play"
    assert cand.asset_type == AssetType.ANDROID_APP
    assert cand.stable_identifier == "com.kaveribank.mobile"
    assert cand.display_name == "Kaveribank Mobile App"


def test_google_play_live_scan_api(client: TestClient):
    """Test full API scan using google_play_snapshot returns CONNECTED and findings."""
    brand = client.post(
        "/api/v1/brands",
        json={"name": "Kaveri Bank", "industry_category": "Banking"},
    ).json()
    brand_id = brand["id"]

    start = client.post(
        "/api/v1/scans",
        json={
            "brand_id": brand_id,
            "mode": "LIVE",
            "source_ids": ["google_play_snapshot"],
        },
    )
    assert start.status_code == 202
    scan_id = start.json()["id"]

    # Poll until completed
    import time
    for _ in range(50):
        detail = client.get(f"/api/v1/scans/{scan_id}").json()
        if detail["status"] in {"COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"}:
            break
        time.sleep(0.1)

    assert detail["status"] == "COMPLETED"
    outcome = detail["source_outcomes"][0]
    assert outcome["source_id"] == "google_play_snapshot"
    assert outcome["status"] == "CONNECTED"
    assert outcome["candidate_count"] >= 4
    assert detail["funnel"]["retrieved"] >= 4
