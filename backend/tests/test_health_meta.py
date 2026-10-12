"""Tests for GET /api/v1/health, /ready, and /meta.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.1
"""

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    """GET /api/v1/health must return contract version 3.0.0 and service status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "threatlens-api"
    assert data["version"] == "3.0.0"
    assert data["contract_version"] == "3.0.0"


def test_ready_endpoint(client: TestClient) -> None:
    """GET /api/v1/ready must return subsystem readiness checks with no secrets."""
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    data = response.json()
    assert data["ready"] is True
    assert "checks" in data
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["config"] == "ok"


def test_meta_endpoint(client: TestClient) -> None:
    """GET /api/v1/meta must return full enum catalog, scoring thresholds, and supported platforms."""
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    data = response.json()
    assert data["scoring_version"] == "3.0.0"
    assert data["contract_version"] == "3.0.0"

    # Thresholds
    thresholds = data["thresholds"]
    assert thresholds["relevance"] == 0.60
    assert thresholds["review"] == 25
    assert thresholds["severity_bands"]["LOW"] == [0, 24]
    assert thresholds["severity_bands"]["MEDIUM"] == [25, 49]
    assert thresholds["severity_bands"]["HIGH"] == [50, 74]
    assert thresholds["severity_bands"]["CRITICAL"] == [75, 100]

    # Enums catalog
    enums = data["enums"]
    assert "ScanMode" in enums
    assert set(enums["ScanMode"]) == {"LIVE", "DEMO"}
    assert "SourceMode" in enums
    assert set(enums["SourceMode"]) == {"LIVE", "CACHED", "SIMULATED"}
    assert "IdentityDecision" in enums
    assert "CANDIDATE_FOR_REVIEW" in enums["IdentityDecision"]
    assert "OFFICIAL_EXACT_MATCH" in enums["IdentityDecision"]

    # Signal tables
    assert "apps" in data["signal_tables"]
    assert "social" in data["signal_tables"]
    app_signals = {
        s["signal_id"]: s["max_points"] for s in data["signal_tables"]["apps"]
    }
    assert app_signals["name_lookalike"] == 25.0
    assert app_signals["publisher_impersonation"] == 20.0
    assert app_signals["icon_similarity"] == 20.0

    # Supported platforms
    platforms = {p["platform"]: p for p in data["supported_platforms"]}
    assert "apple_app_store" in platforms
    assert "bluesky" in platforms
    assert platforms["apple_app_store"]["connected"] is True
    assert platforms["google_play"]["connected"] is False
