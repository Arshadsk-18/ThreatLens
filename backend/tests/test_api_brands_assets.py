"""Tests for P0 Brand and Official Asset endpoints.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 11.2, 11.3
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.memory_store import get_memory_store
from app.schemas.enums import ApiErrorCode


@pytest.fixture(autouse=True)
def clean_memory_store():
    """Ensure in-memory store is reset for each test."""
    store = get_memory_store()
    store.clear()
    yield
    store.clear()


# ============================================================================
# Brand Routes Tests (Section 11.2)
# ============================================================================


def test_create_brand_success(client: TestClient) -> None:
    """POST /api/v1/brands creates a new brand and returns 201."""
    payload = {
        "name": "Kaveri Bank",
        "description": "Fictional demo bank",
        "official_domains": ["kaveribank.example"],
        "keywords": ["Kaveri Bank", "KaveriBank"],
        "distinctive_tokens": ["kaveri"],
        "industry_category": "Finance",
        "demo_brand": True,
    }
    response = client.post("/api/v1/brands", json=payload)
    assert response.status_code == 201
    assert "X-Request-ID" in response.headers

    data = response.json()
    assert data["name"] == "Kaveri Bank"
    assert data["demo_brand"] is True
    assert data["official_domains"] == ["kaveribank.example"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_brand_validation_errors(client: TestClient) -> None:
    """POST /api/v1/brands enforces name length, domain hostname rules, and keywords cap."""
    # 1. Name too short (< 2 chars)
    r1 = client.post("/api/v1/brands", json={"name": "K"})
    assert r1.status_code == 422
    assert r1.json()["error"]["code"] == ApiErrorCode.VALIDATION_ERROR.value

    # 2. Domain has scheme or path (must be hostname only)
    r2 = client.post(
        "/api/v1/brands",
        json={
            "name": "Kaveri Bank",
            "official_domains": ["https://kaveribank.example/login"],
        },
    )
    assert r2.status_code == 422
    assert r2.json()["error"]["code"] == ApiErrorCode.VALIDATION_ERROR.value

    # 3. Keywords > 12
    r3 = client.post(
        "/api/v1/brands",
        json={
            "name": "Kaveri Bank",
            "keywords": [f"keyword_{i}" for i in range(13)],
        },
    )
    assert r3.status_code == 422
    assert r3.json()["error"]["code"] == ApiErrorCode.VALIDATION_ERROR.value


def test_get_and_list_brands(client: TestClient) -> None:
    """GET /api/v1/brands lists brands with pagination; GET /brands/{id} retrieves details."""
    # Create two brands
    b1 = client.post("/api/v1/brands", json={"name": "Brand Alpha"}).json()
    b2 = client.post("/api/v1/brands", json={"name": "Brand Beta"}).json()
    assert b2["name"] == "Brand Beta"

    # List
    list_res = client.get("/api/v1/brands?limit=10&offset=0")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["limit"] == 10
    assert data["offset"] == 0

    # Get by ID
    get_res = client.get(f"/api/v1/brands/{b1['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Brand Alpha"

    # Get non-existent
    bad_id = str(uuid.uuid4())
    bad_res = client.get(f"/api/v1/brands/{bad_id}")
    assert bad_res.status_code == 404
    assert bad_res.json()["error"]["code"] == ApiErrorCode.NOT_FOUND.value


def test_patch_brand(client: TestClient) -> None:
    """PATCH /api/v1/brands/{id} updates permitted fields."""
    b = client.post("/api/v1/brands", json={"name": "Original Name"}).json()

    patch_res = client.patch(
        f"/api/v1/brands/{b['id']}",
        json={"description": "Updated Description", "keywords": ["updated", "words"]},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["name"] == "Original Name"
    assert updated["description"] == "Updated Description"
    assert updated["keywords"] == ["updated", "words"]


def test_brand_summary(client: TestClient) -> None:
    """GET /api/v1/brands/{id}/summary returns overview aggregate counters."""
    b = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = b["id"]

    summary_res = client.get(f"/api/v1/brands/{b_id}/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["brand_id"] == b_id
    assert summary["official_asset_count"] == 0
    assert "funnel" in summary
    assert "findings_by_severity" in summary


# ============================================================================
# Prefill Routes Tests (Section 11.3)
# ============================================================================


def test_prefill_apple_store_url_success(client: TestClient) -> None:
    """Allowlisted Apple App Store URL extracts trackId and returns prefill draft."""
    b = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = b["id"]

    url = "https://apps.apple.com/in/app/kaveri-bank/id1234567890"
    res = client.post(f"/api/v1/brands/{b_id}/assets/prefill", json={"url": url})
    assert res.status_code == 200

    data = res.json()
    assert data["source_id"] == "apple_itunes"
    assert data["source_status"] == "CONNECTED"
    assert data["draft"] is not None

    draft = data["draft"]
    assert draft["asset_type"] == "IOS_APP"
    assert draft["platform"] == "apple_app_store"
    assert draft["stable_identifier"] == "1234567890"
    assert draft["publisher_name"] == "Kaveri Bank Ltd"
    assert draft["relationship"] == "OFFICIAL"
    assert draft["trust_publisher"] is True

    # Critical check: prefill is draft-only and never persists an asset!
    assets_res = client.get(f"/api/v1/brands/{b_id}/assets")
    assert assets_res.json()["total"] == 0


def test_prefill_bluesky_url_success(client: TestClient) -> None:
    """Allowlisted Bluesky profile URL extracts handle and returns prefill draft."""
    b = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = b["id"]

    url = "https://bsky.app/profile/kaveribank.example"
    res = client.post(f"/api/v1/brands/{b_id}/assets/prefill", json={"url": url})
    assert res.status_code == 200

    data = res.json()
    assert data["source_id"] == "bluesky_public"
    assert data["draft"] is not None
    assert data["draft"]["asset_type"] == "SOCIAL_ACCOUNT"
    assert data["draft"]["platform"] == "bluesky"
    assert data["draft"]["handle"] == "kaveribank.example"


def test_prefill_blocks_unlisted_urls(client: TestClient) -> None:
    """Prefill rejects non-allowlisted arbitrary URLs with 422 VALIDATION_ERROR and BLOCKED_URL."""
    b = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = b["id"]

    disallowed_urls = [
        "https://malicious.example.com/exploit",
        "https://google.com/search?q=bank",
        "https://apps.apple.com.attacker.com/app/id123",
        "http://insecure.apple.com/app/id123",
    ]

    for bad_url in disallowed_urls:
        res = client.post(
            f"/api/v1/brands/{b_id}/assets/prefill", json={"url": bad_url}
        )
        assert res.status_code == 422
        err = res.json()["error"]
        assert err["code"] == ApiErrorCode.VALIDATION_ERROR.value
        assert any("BLOCKED_URL" in detail["issue"] for detail in err["details"])


def test_prefill_provider_failure_returns_200_with_null_draft(
    client: TestClient,
) -> None:
    """When store lookup fails, prefill returns HTTP 200 with draft=null for manual entry."""
    b = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = b["id"]

    # Identifier 'fail' signals lookup failure in test double
    res = client.post(
        f"/api/v1/brands/{b_id}/assets/prefill",
        json={"platform": "apple_app_store", "identifier": "fail"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["draft"] is None
    assert data["source_status"] == "ERROR"
    assert data["error_code"] == "PROVIDER_UNAVAILABLE"


# ============================================================================
# Official Asset Registration & Management Tests (Section 11.3)
# ============================================================================


def test_register_asset_success(client: TestClient) -> None:
    """POST /api/v1/brands/{id}/assets registers a valid official asset."""
    b = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = b["id"]

    payload = {
        "asset_type": "IOS_APP",
        "platform": "apple_app_store",
        "stable_identifier": "1234567890",
        "secondary_identifiers": {"bundle_id": "com.kaveribank.mobile"},
        "developer_id": "9000000001",
        "publisher_name": "Kaveri Bank Ltd",
        "display_name": "Kaveri Bank",
        "relationship": "OFFICIAL",
        "verification_method": "STORE_LOOKUP",
        "is_verified": True,
        "trust_publisher": True,
        "notes": "Official iOS app",
    }
    res = client.post(f"/api/v1/brands/{b_id}/assets", json=payload)
    assert res.status_code == 201

    data = res.json()
    assert data["stable_identifier"] == "1234567890"
    assert data["is_verified"] is True
    assert data["brand_id"] == b_id

    # Verify asset is now listed
    list_res = client.get(f"/api/v1/brands/{b_id}/assets")
    assert list_res.json()["total"] == 1


def test_register_duplicate_asset_returns_409_conflict(client: TestClient) -> None:
    """Registering duplicate (brand_id, platform, stable_identifier) returns 409 CONFLICT."""
    b = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = b["id"]

    payload = {
        "asset_type": "IOS_APP",
        "platform": "apple_app_store",
        "stable_identifier": "1234567890",
        "display_name": "Kaveri Bank",
    }

    # First succeeds
    r1 = client.post(f"/api/v1/brands/{b_id}/assets", json=payload)
    assert r1.status_code == 201

    # Second returns 409 CONFLICT
    r2 = client.post(f"/api/v1/brands/{b_id}/assets", json=payload)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == ApiErrorCode.CONFLICT.value


def test_stable_identifier_platform_syntax_validation(client: TestClient) -> None:
    """Stable identifiers must satisfy platform-specific syntax rules."""
    b = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = b["id"]

    # 1. apple_app_store must be numeric
    r1 = client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "IOS_APP",
            "platform": "apple_app_store",
            "stable_identifier": "not-a-number",
            "display_name": "Invalid App",
        },
    )
    assert r1.status_code == 422
    assert "numeric" in r1.json()["error"]["details"][0]["issue"]

    # 2. google_play must be valid package name
    r2 = client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "ANDROID_APP",
            "platform": "google_play",
            "stable_identifier": "invalid_single_token",
            "display_name": "Invalid App",
        },
    )
    assert r2.status_code == 422
    assert "package name" in r2.json()["error"]["details"][0]["issue"]

    # 3. bluesky must be did: string
    r3 = client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "SOCIAL_ACCOUNT",
            "platform": "bluesky",
            "stable_identifier": "just_a_handle.bsky.social",
            "display_name": "Invalid Account",
        },
    )
    assert r3.status_code == 422
    assert "did:" in r3.json()["error"]["details"][0]["issue"]


def test_publisher_discrepancy_warning(client: TestClient) -> None:
    """A warning is returned when an official asset's publisher differs from other official assets."""
    b = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = b["id"]

    # First asset with publisher 'Kaveri Bank Ltd'
    client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "IOS_APP",
            "platform": "apple_app_store",
            "stable_identifier": "111111",
            "display_name": "App One",
            "publisher_name": "Kaveri Bank Ltd",
            "relationship": "OFFICIAL",
        },
    )

    # Second asset with different publisher 'Unrelated Publisher Inc'
    r2 = client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "IOS_APP",
            "platform": "apple_app_store",
            "stable_identifier": "222222",
            "display_name": "App Two",
            "publisher_name": "Unrelated Publisher Inc",
            "relationship": "OFFICIAL",
        },
    )
    assert r2.status_code == 201
    assert r2.json()["warning"] is not None
    assert "differs" in r2.json()["warning"]


def test_patch_asset_and_audit_event(client: TestClient) -> None:
    """PATCH /brands/{id}/assets/{asset_id} updates asset and writes audit event."""
    b = client.post("/api/v1/brands", json={"name": "Kaveri Bank"}).json()
    b_id = b["id"]

    asset = client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "IOS_APP",
            "platform": "apple_app_store",
            "stable_identifier": "123456",
            "display_name": "Kaveri Bank App",
        },
    ).json()
    asset_id = asset["id"]

    patch_res = client.patch(
        f"/api/v1/brands/{b_id}/assets/{asset_id}",
        json={"is_active": False, "notes": "Deactivated by compliance team"},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["is_active"] is False
    assert updated["notes"] == "Deactivated by compliance team"

    # Verify audit event was logged in store
    store = get_memory_store()
    assert len(store.audit_events) == 1
    event = store.audit_events[0]
    assert event["event_type"] == "ASSET_DEACTIVATED"
    assert event["entity_id"] == uuid.UUID(asset_id)
    assert event["details"]["is_active"]["new"] is False
