"""Section 18.3 Must-Pass Automated Tests for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 18.3

This file contains the complete test suite mandated by Section 18.3:
1. test_openapi_matches_contract
2. test_scan_funnel_invariant
3. test_official_app_never_flagged
4. test_official_social_never_flagged
5. test_publisher_id_clears_second_app
6. test_namesake_not_flagged
7. test_name_only_capped_at_medium
8. test_lookalike_techniques
9. test_live_scan_has_no_simulated_records
10. test_demo_scan_makes_no_network_calls
11. test_provider_failure_is_not_clean_result
12. test_not_connected_is_not_an_error
13. test_prefill_rejects_unlisted_urls
14. test_image_fetch_blocks_non_allowlisted_hosts
15. test_decision_memory_persists
16. test_eval_metrics_computed_not_hardcoded
17. test_name_similarity_vectors
18. test_wilson_interval
19. test_api_error_http_mapping
20. test_declared_unofficial_cannot_hide_copied_avatar
21. test_declared_unofficial_requires_clean_lure_and_links
22. test_g5_never_applies_to_exact_name_or_homoglyph
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from app.core.errors import (
    ConflictException,
    ModeNotAllowedException,
    NotFoundException,
    RateLimitedException,
    ScanAlreadyRunningException,
    UnauthorizedException,
    ValidationException,
)
from app.core.prefill_service import register_source_adapter
from app.main import app
from app.schemas.candidate import NormalizedCandidate, QueryPlan, SourceResult
from app.schemas.context import BrandCtx
from app.schemas.enums import (
    ApiErrorCode,
    AssetType,
    Severity,
    SourceMode,
    SourceStatus,
)
from app.schemas.scoring import ScoringConfig
from app.schemas.source import SourceHealth
from app.services.assess import assess
from app.services.image_fetch import fetch_icon_hash


class MockScanAdapter:
    """Mock adapter for deterministic scan pipeline testing."""

    def __init__(self, candidates: list[NormalizedCandidate]) -> None:
        self.candidates = candidates
        self.source_id = "apple_itunes"

    async def health_check(self) -> SourceHealth:
        return SourceHealth(
            source_id=self.source_id,
            status=SourceStatus.CONNECTED,
            latency_ms=10,
        )

    async def search(
        self,
        plan: QueryPlan,
        limit: int,
        *,
        force_refresh: bool,
        allow_stale_cache: bool,
    ) -> SourceResult:
        return SourceResult(
            source_id=self.source_id,
            status=SourceStatus.CONNECTED,
            source_mode=SourceMode.LIVE,
            queries_executed=len(plan.queries),
            candidates=self.candidates[:limit],
            cache_hit_count=0,
            duration_ms=25,
            retrieved_at=datetime.now(timezone.utc),
        )

    async def lookup(self, identifier: str) -> NormalizedCandidate | None:
        for c in self.candidates:
            if c.stable_identifier == identifier:
                return c
        return None


def _wait_for_scan(client: TestClient, scan_id: str) -> dict:
    for _ in range(30):
        res = client.get(f"/api/v1/scans/{scan_id}")
        data = res.json()
        if data["status"] in {"COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"}:
            return data
    raise TimeoutError("Scan timed out in test")


# ---------------------------------------------------------------------------
# Section 18.3 Test 1: OpenAPI Schema Conformance
# ---------------------------------------------------------------------------
def test_openapi_matches_contract() -> None:
    """The generated OpenAPI schema must match docs/openapi.snapshot.json exactly."""
    snapshot_path = (
        Path(__file__).resolve().parent.parent.parent / "docs" / "openapi.snapshot.json"
    )
    assert snapshot_path.exists(), f"Snapshot file not found at {snapshot_path}"
    committed = json.loads(snapshot_path.read_text(encoding="utf-8"))
    generated = app.openapi()
    assert generated == committed, "OpenAPI schema drifted from docs/openapi.snapshot.json"


# ---------------------------------------------------------------------------
# Section 18.3 Test 2: Scan Funnel Invariant
# ---------------------------------------------------------------------------
def test_scan_funnel_invariant(client: TestClient) -> None:
    """Enforce: deduplicated == official_cleared + not_relevant + benign_lookalike + below_threshold + findings."""
    brand = client.post("/api/v1/brands", json={"name": "Funnel Test Brand", "industry_category": "Banking"}).json()
    b_id = brand["id"]

    now = datetime.now(timezone.utc)
    candidates = [
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="c_unique_1",
            display_name="Funnel Test Brand Lookalike",
            developer_id="9000000042",
            category="Banking",
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="c_unique_1",  # duplicate
            display_name="Funnel Test Brand Lookalike",
            developer_id="9000000042",
            category="Banking",
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
    ]
    register_source_adapter("apple_itunes", MockScanAdapter(candidates))

    start = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]})
    scan = _wait_for_scan(client, start.json()["id"])
    funnel = scan["funnel"]

    assert funnel["retrieved"] == 2
    assert funnel["deduplicated"] == 1
    assert funnel["retrieved"] >= funnel["deduplicated"]
    assert funnel["deduplicated"] == (
        funnel["official_cleared"]
        + funnel["not_relevant"]
        + funnel["benign_lookalike"]
        + funnel["below_threshold"]
        + funnel["findings"]
    )


# ---------------------------------------------------------------------------
# Section 18.3 Test 3: Official App Never Flagged
# ---------------------------------------------------------------------------
def test_official_app_never_flagged(client: TestClient) -> None:
    """Official app matching exact stable_identifier must be cleared and never appear in findings."""
    brand = client.post("/api/v1/brands", json={"name": "SecureBank", "industry_category": "Finance"}).json()
    b_id = brand["id"]

    client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "IOS_APP",
            "platform": "apple_app_store",
            "stable_identifier": "1234500001",
            "developer_id": "8000000001",
            "display_name": "SecureBank Official",
            "is_verified": True,
        },
    )

    now = datetime.now(timezone.utc)
    candidates = [
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="1234500001",
            display_name="SecureBank Official",
            developer_id="8000000001",
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
    ]
    register_source_adapter("apple_itunes", MockScanAdapter(candidates))

    start = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]})
    scan_id = start.json()["id"]
    _wait_for_scan(client, scan_id)

    findings = client.get(f"/api/v1/scans/{scan_id}/findings").json()
    assert findings["total"] == 0, "Official app must NEVER be flagged as a finding"

    cleared = client.get(f"/api/v1/scans/{scan_id}/cleared").json()
    assert cleared["total"] == 1
    assert cleared["items"][0]["decision"] == "OFFICIAL_EXACT_MATCH"


# ---------------------------------------------------------------------------
# Section 18.3 Test 4: Official Social Never Flagged
# ---------------------------------------------------------------------------
def test_official_social_never_flagged(client: TestClient) -> None:
    """Official social account matching stable handle must be cleared and never appear in findings."""
    brand = client.post("/api/v1/brands", json={"name": "SocialBank", "industry_category": "Finance"}).json()
    b_id = brand["id"]

    res = client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "SOCIAL_ACCOUNT",
            "platform": "bluesky",
            "stable_identifier": "did:plc:socialbank12345",
            "display_name": "SocialBank Official",
            "is_verified": True,
        },
    )
    assert res.status_code == 201

    now = datetime.now(timezone.utc)
    candidates = [
        NormalizedCandidate(
            source_id="bluesky_public",
            platform="bluesky",
            asset_type=AssetType.SOCIAL_ACCOUNT,
            stable_identifier="did:plc:socialbank12345",
            display_name="SocialBank Official",
            handle="socialbank.bsky.social",
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
    ]

    class MockBlueskyAdapter(MockScanAdapter):
        def __init__(self, candidates):
            super().__init__(candidates)
            self.source_id = "bluesky_public"

    register_source_adapter("bluesky_public", MockBlueskyAdapter(candidates))

    start = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["bluesky_public"]})
    scan_id = start.json()["id"]
    _wait_for_scan(client, scan_id)

    findings = client.get(f"/api/v1/scans/{scan_id}/findings").json()
    assert findings["total"] == 0

    cleared = client.get(f"/api/v1/scans/{scan_id}/cleared").json()
    assert cleared["total"] == 1
    assert cleared["items"][0]["decision"] == "OFFICIAL_EXACT_MATCH"


# ---------------------------------------------------------------------------
# Section 18.3 Test 5: Publisher ID Clears Second App
# ---------------------------------------------------------------------------
def test_publisher_id_clears_second_app(client: TestClient) -> None:
    """Second app with different ID but matching trusted publisher/developer ID must be cleared."""
    brand = client.post("/api/v1/brands", json={"name": "TrustCorp", "industry_category": "Tech"}).json()
    b_id = brand["id"]

    client.post(
        f"/api/v1/brands/{b_id}/assets",
        json={
            "asset_type": "IOS_APP",
            "platform": "apple_app_store",
            "stable_identifier": "10001",
            "developer_id": "DEV_TRUSTED_99",
            "display_name": "TrustCorp Core",
            "is_verified": True,
            "trust_publisher": True,
        },
    )

    now = datetime.now(timezone.utc)
    candidates = [
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="10002",  # Different app ID
            display_name="TrustCorp Pro",
            developer_id="DEV_TRUSTED_99",  # Matching developer ID
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
    ]
    register_source_adapter("apple_itunes", MockScanAdapter(candidates))

    start = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]})
    scan_id = start.json()["id"]
    _wait_for_scan(client, scan_id)

    findings = client.get(f"/api/v1/scans/{scan_id}/findings").json()
    assert findings["total"] == 0

    cleared = client.get(f"/api/v1/scans/{scan_id}/cleared").json()
    assert cleared["total"] == 1
    assert cleared["items"][0]["decision"] == "OFFICIAL_PUBLISHER_MATCH"


# ---------------------------------------------------------------------------
# Section 18.3 Test 6: Legitimate Namesake Not Flagged
# ---------------------------------------------------------------------------
def test_namesake_not_flagged(client: TestClient) -> None:
    """Unrelated namesake in distinct category must be cleared via G4 and never flagged."""
    brand = client.post("/api/v1/brands", json={"name": "Apex Finance", "industry_category": "Finance"}).json()
    b_id = brand["id"]

    now = datetime.now(timezone.utc)
    candidates = [
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="999888777",
            display_name="Apex Coffee Roasters",
            category="Food & Drink",  # Distinct category
            developer_id="DEV_COFFEE_1",
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
        ),
    ]
    register_source_adapter("apple_itunes", MockScanAdapter(candidates))

    start = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]})
    scan_id = start.json()["id"]
    _wait_for_scan(client, scan_id)

    findings = client.get(f"/api/v1/scans/{scan_id}/findings").json()
    assert findings["total"] == 0

    cleared = client.get(f"/api/v1/scans/{scan_id}/cleared").json()
    assert cleared["total"] == 1
    assert cleared["items"][0]["decision"] == "BENIGN_LOOKALIKE"


# ---------------------------------------------------------------------------
# Section 18.3 Test 7: Name-Only Match Capped at Medium (G2/G3)
# ---------------------------------------------------------------------------
@pytest.mark.xfail(reason="Blocked on Person 4 feat/detection implementation of assess()")
def test_name_only_capped_at_medium() -> None:
    """A similar name alone without secondary evidence must never produce score > 59 or HIGH/CRITICAL severity."""
    now = datetime.now(timezone.utc)
    cand = NormalizedCandidate(
        source_id="apple_itunes",
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier="candidate_name_only",
        display_name="Kaveri Bank Helper",
        source_mode=SourceMode.LIVE,
        retrieved_at=now,
    )
    brand = BrandCtx(id=None, name="Kaveri Bank", industry_category="Finance")
    result = assess(cand, brand, [], ScoringConfig())
    assert result.risk_score <= 59
    assert result.severity in {Severity.LOW, Severity.MEDIUM}


# ---------------------------------------------------------------------------
# Section 18.3 Test 8: Lookalike Techniques Coverage
# ---------------------------------------------------------------------------
@pytest.mark.xfail(reason="Blocked on Person 4 feat/detection implementation of normalization and techniques")
def test_lookalike_techniques() -> None:
    """Detection of lookalike techniques: homoglyphs, added-word, separators, etc."""
    raise NotImplementedError("Person 4 owns lookalike technique analysis.")


# ---------------------------------------------------------------------------
# Section 18.3 Test 9: LIVE Scan Has No Simulated Records
# ---------------------------------------------------------------------------
def test_live_scan_has_no_simulated_records(client: TestClient) -> None:
    """LIVE scans must reject SIMULATED records and never output simulated source modes."""
    brand = client.post("/api/v1/brands", json={"name": "LiveTest", "industry_category": "Tech"}).json()
    b_id = brand["id"]

    now = datetime.now(timezone.utc)
    simulated_candidates = [
        NormalizedCandidate(
            source_id="apple_itunes",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="sim_1",
            display_name="Simulated Asset",
            source_mode=SourceMode.SIMULATED,
            retrieved_at=now,
        ),
    ]
    register_source_adapter("apple_itunes", MockScanAdapter(simulated_candidates))

    start = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]})
    scan = _wait_for_scan(client, start.json()["id"])
    assert scan["status"] == "FAILED"
    assert "MODE_NOT_ALLOWED" in (scan.get("error_message") or "")


# ---------------------------------------------------------------------------
# Section 18.3 Test 10: DEMO Scan Makes No Network Calls
# ---------------------------------------------------------------------------
def test_demo_scan_makes_no_network_calls(client: TestClient) -> None:
    """DEMO scans must execute entirely offline using local test doubles with zero outbound network calls."""
    from app.core.prefill_service import register_source_adapter
    from app.schemas.candidate import QueryPlan, SourceResult

    class ExplosiveLiveAdapter:
        source_id = "apple_itunes"
        called = False

        async def search(self, plan: QueryPlan, limit: int, **kwargs) -> SourceResult:
            ExplosiveLiveAdapter.called = True
            raise AssertionError("Live adapter must never be invoked in DEMO scan!")

        async def health_check(self):
            pass

        async def lookup(self, identifier: str):
            return None

    explosive = ExplosiveLiveAdapter()
    register_source_adapter("apple_itunes", explosive)

    brand = client.post("/api/v1/brands", json={"name": "DemoBrand", "industry_category": "Banking"}).json()
    b_id = brand["id"]

    with patch("socket.socket.connect", side_effect=RuntimeError("Socket connect attempted in DEMO scan!")), \
         patch("httpx.AsyncClient.request", side_effect=RuntimeError("httpx request attempted in DEMO scan!")), \
         patch("httpx.AsyncClient.get", side_effect=RuntimeError("Outbound network call attempted during DEMO scan!")), \
         patch("httpx.AsyncClient.post", side_effect=RuntimeError("Outbound network call attempted during DEMO scan!")):
        start = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "DEMO", "source_ids": ["apple_itunes", "bluesky_public"]})
        assert start.status_code == 202
        scan = _wait_for_scan(client, start.json()["id"])
        assert scan["status"] == "COMPLETED"

    assert explosive.called is False, "Live adapter was invoked during DEMO scan!"
    findings = client.get(f"/api/v1/scans/{scan['id']}/findings").json()["items"]
    for f in findings:
        assert f["source_mode"] == "SIMULATED"


# ---------------------------------------------------------------------------
# Section 18.3 Test 11: Provider Failure Is Not Clean Result
# ---------------------------------------------------------------------------
def test_provider_failure_is_not_clean_result(client: TestClient) -> None:
    """Provider failure (e.g. 429/timeout) must leave visible error outcome, not a clean 0-result."""
    brand = client.post("/api/v1/brands", json={"name": "FailTest", "industry_category": "Banking"}).json()
    b_id = brand["id"]

    class FailingAdapter(MockScanAdapter):
        async def search(self, plan, limit, *, force_refresh, allow_stale_cache):
            raise RuntimeError("Upstream 429 Rate Limit Exceeded")

    register_source_adapter("apple_itunes", FailingAdapter([]))

    start = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]})
    scan = _wait_for_scan(client, start.json()["id"])
    outcome = scan["source_outcomes"][0]
    assert outcome["status"] == "ERROR"
    assert outcome["error_code"] == "PROVIDER_UNAVAILABLE"


# ---------------------------------------------------------------------------
# Section 18.3 Test 12: NOT_CONNECTED Is Not An Error
# ---------------------------------------------------------------------------
def test_not_connected_is_not_an_error(client: TestClient) -> None:
    """Unconnected sources must show NOT_CONNECTED and not fail the scan."""
    brand = client.post("/api/v1/brands", json={"name": "NotConnTest", "industry_category": "Banking"}).json()
    b_id = brand["id"]

    start = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["instagram"]})
    scan = _wait_for_scan(client, start.json()["id"])
    assert scan["status"] == "COMPLETED"
    outcome = scan["source_outcomes"][0]
    assert outcome["status"] == "NOT_CONNECTED"


# ---------------------------------------------------------------------------
# Section 18.3 Test 13: Prefill Rejects Unlisted URLs
# ---------------------------------------------------------------------------
def test_prefill_rejects_unlisted_urls(client: TestClient) -> None:
    """Prefill endpoint must reject non-allowlisted domains with 422 validation error."""
    brand = client.post("/api/v1/brands", json={"name": "PrefillTest", "industry_category": "Tech"}).json()
    b_id = brand["id"]

    res = client.post(f"/api/v1/brands/{b_id}/assets/prefill", json={"url": "https://evil.phishing.site/app/123"})
    assert res.status_code == 422
    err = res.json()["error"]
    assert err["code"] in {"VALIDATION_ERROR", "BLOCKED_URL"}


# ---------------------------------------------------------------------------
# Section 18.3 Test 14: Safe Image Fetch Blocks Non-Allowlisted Hosts
# ---------------------------------------------------------------------------
@pytest.mark.xfail(reason="Blocked on Person 3 feat/discovery implementation of fetch_icon_hash()")
@pytest.mark.anyio
async def test_image_fetch_blocks_non_allowlisted_hosts() -> None:
    """fetch_icon_hash must block SSRF / non-allowlisted hosts and return None."""
    res = await fetch_icon_hash("https://malicious-internal-metadata.corp/icon.png")
    assert res is None


# ---------------------------------------------------------------------------
# Section 18.3 Test 15: Decision Memory Persists
# ---------------------------------------------------------------------------
def test_decision_memory_persists(client: TestClient) -> None:
    """Analyst decisions must persist across scans and update candidate review status."""
    brand = client.post("/api/v1/brands", json={"name": "DecisionTest", "industry_category": "Finance"}).json()
    b_id = brand["id"]

    now = datetime.now(timezone.utc)
    cand = NormalizedCandidate(
        source_id="apple_itunes",
        platform="apple_app_store",
        asset_type=AssetType.IOS_APP,
        stable_identifier="persist_cand_99",
        display_name="DecisionTest Scam App",
        developer_id="DEV_SCAM_1",
        category="Finance",
        source_mode=SourceMode.LIVE,
        retrieved_at=now,
    )
    register_source_adapter("apple_itunes", MockScanAdapter([cand]))

    start = client.post("/api/v1/scans", json={"brand_id": b_id, "mode": "LIVE", "source_ids": ["apple_itunes"]})
    scan_id = start.json()["id"]
    _wait_for_scan(client, scan_id)

    findings = client.get(f"/api/v1/scans/{scan_id}/findings").json()
    finding_id = findings["items"][0]["id"]

    # Analyst decision
    patch_res = client.patch(
        f"/api/v1/findings/{finding_id}",
        json={
            "status": "CONFIRMED_SUSPICIOUS",
            "decision_reason": "Verified brand asset spoofing attempt.",
            "notes": "Escalated for takedown.",
        },
    )
    assert patch_res.status_code == 200

    # Verify decision reflected in finding detail
    detail = client.get(f"/api/v1/findings/{finding_id}").json()
    assert detail["status"] == "CONFIRMED_SUSPICIOUS"
    assert len(detail["decision_history"]) >= 1
    assert detail["decision_history"][-1]["decision_reason"] == "Verified brand asset spoofing attempt."


# ---------------------------------------------------------------------------
# Section 18.3 Test 16: Evaluation Metrics Computed Not Hardcoded
# ---------------------------------------------------------------------------
@pytest.mark.xfail(reason="Blocked on Person 4 feat/detection implementation of evaluation harness")
def test_eval_metrics_computed_not_hardcoded() -> None:
    """Evaluation metrics must be computed from dataset rather than hardcoded."""
    raise NotImplementedError("Person 4 owns offline evaluation harness.")


# ---------------------------------------------------------------------------
# Section 18.3 Test 17: Name Similarity Vectors
# ---------------------------------------------------------------------------
@pytest.mark.xfail(reason="Blocked on Person 4 feat/detection implementation of name similarity formula")
def test_name_similarity_vectors() -> None:
    """40+ name vector pairs must evaluate to expected scores per Section 8.1 formula."""
    raise NotImplementedError("Person 4 owns name vector scoring.")


# ---------------------------------------------------------------------------
# Section 18.3 Test 18: Wilson Interval
# ---------------------------------------------------------------------------
@pytest.mark.xfail(reason="Blocked on Person 4 feat/detection implementation of Wilson interval")
def test_wilson_interval() -> None:
    """Wilson score confidence interval for binomial proportions."""
    raise NotImplementedError("Person 4 owns Wilson interval computation.")


# ---------------------------------------------------------------------------
# Section 18.3 Test 19: API Error HTTP Mapping
# ---------------------------------------------------------------------------
def test_api_error_http_mapping() -> None:
    """All contract error codes must map to their documented HTTP status codes per Section 10."""
    mapping = {
        ValidationException: (422, ApiErrorCode.VALIDATION_ERROR),
        NotFoundException: (404, ApiErrorCode.NOT_FOUND),
        ConflictException: (409, ApiErrorCode.CONFLICT),
        ScanAlreadyRunningException: (409, ApiErrorCode.SCAN_ALREADY_RUNNING),
        ModeNotAllowedException: (422, ApiErrorCode.MODE_NOT_ALLOWED),
        RateLimitedException: (429, ApiErrorCode.RATE_LIMITED),
        UnauthorizedException: (401, ApiErrorCode.UNAUTHORIZED),
    }
    for exc_cls, (expected_status, expected_code) in mapping.items():
        exc = exc_cls("Test error message")
        assert exc.status_code == expected_status, f"{exc_cls} status mismatch"
        assert exc.code == expected_code, f"{exc_cls} code mismatch"


# ---------------------------------------------------------------------------
# Section 18.3 Tests 20-22: G5 Safeguard Tests
# ---------------------------------------------------------------------------
@pytest.mark.xfail(reason="Blocked on Person 4 feat/detection implementation of G5 safeguards")
def test_declared_unofficial_cannot_hide_copied_avatar() -> None:
    """G5 safeguard: Declared unofficial status cannot hide copied avatar (phash >= 0.85)."""
    raise NotImplementedError("Person 4 owns G5 safeguard implementation.")


@pytest.mark.xfail(reason="Blocked on Person 4 feat/detection implementation of G5 safeguards")
def test_declared_unofficial_requires_clean_lure_and_links() -> None:
    """G5 safeguard: Declared unofficial status requires clean lure terms and no phishing links."""
    raise NotImplementedError("Person 4 owns G5 safeguard implementation.")


@pytest.mark.xfail(reason="Blocked on Person 4 feat/detection implementation of G5 safeguards")
def test_g5_never_applies_to_exact_name_or_homoglyph() -> None:
    """G5 safeguard: G5 disclaimer defense never applies to exact name reuse or homoglyphs."""
    raise NotImplementedError("Person 4 owns G5 safeguard implementation.")
