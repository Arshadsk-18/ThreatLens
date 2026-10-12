"""OpenAPI contract conformance test.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 0.4, 10, 11
"""

import json
from pathlib import Path

from app.main import app
from app.schemas.enums import (
    ApiErrorCode,
    AssetType,
    EvalLabel,
    EvalProvenance,
    EvalSplit,
    EvidenceGroup,
    EvidenceStatus,
    FindingStatus,
    IdentityDecision,
    LookalikeTechnique,
    ProviderErrorCode,
    Relationship,
    ScanMode,
    ScanStage,
    ScanStatus,
    Severity,
    SourceMode,
    SourceStatus,
    VerificationMethod,
)


def test_openapi_matches_snapshot() -> None:
    """The generated OpenAPI specification must exactly match the committed snapshot.

    If this fails, do not weaken the test or alter the snapshot merely to hide a mismatch.
    Any additive contract change requires following the protocol in Section 0.
    """
    snapshot_path = (
        Path(__file__).resolve().parent.parent.parent / "docs" / "openapi.snapshot.json"
    )
    assert snapshot_path.exists(), f"Snapshot file not found at {snapshot_path}"

    committed_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    generated_schema = app.openapi()

    assert generated_schema == committed_snapshot, (
        "Generated OpenAPI schema has drifted from docs/openapi.snapshot.json! "
        "Review diff before committing changes."
    )


def test_openapi_all_contract_paths_and_operations_exist() -> None:
    """All 19 contract routes across Sections 11.1 to 11.5 must exist with required HTTP methods."""
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    expected_operations = {
        "/api/v1/health": ["get"],
        "/api/v1/ready": ["get"],
        "/api/v1/meta": ["get"],
        "/api/v1/sources/status": ["get"],
        "/api/v1/brands": ["get", "post"],
        "/api/v1/brands/{brand_id}": ["get", "patch"],
        "/api/v1/brands/{brand_id}/summary": ["get"],
        "/api/v1/brands/{brand_id}/assets/prefill": ["post"],
        "/api/v1/brands/{brand_id}/assets": ["get", "post"],
        "/api/v1/brands/{brand_id}/assets/{asset_id}": ["get", "patch"],
        "/api/v1/brands/{brand_id}/cleared": ["get"],
        "/api/v1/brands/{brand_id}/audit": ["get"],
        "/api/v1/scans": ["get", "post"],
        "/api/v1/scans/{scan_id}": ["get"],
        "/api/v1/scans/{scan_id}/findings": ["get"],
        "/api/v1/scans/{scan_id}/cleared": ["get"],
        "/api/v1/findings": ["get"],
        "/api/v1/findings/{finding_id}": ["get", "patch"],
        "/api/v1/findings/{finding_id}/comparison": ["get"],
    }

    assert len(expected_operations) == 19
    for path, methods in expected_operations.items():
        assert path in paths, f"Required contract path {path} missing from OpenAPI schema!"
        for m in methods:
            assert m in paths[path], f"Method {m.upper()} missing on path {path}!"


def test_openapi_contract_parameters_and_responses() -> None:
    """Verify parameters, response codes, and schemas across critical contract endpoints."""
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    # 1. /sources/status has refresh parameter
    sources_get = paths["/api/v1/sources/status"]["get"]
    param_names = [p["name"] for p in sources_get.get("parameters", [])]
    assert "refresh" in param_names
    assert "200" in sources_get.get("responses", {})

    # 2. /findings has filters and pagination
    findings_get = paths["/api/v1/findings"]["get"]
    f_params = [p["name"] for p in findings_get.get("parameters", [])]
    for required_filter in [
        "brand_id", "scan_id", "status", "asset_type", "platform",
        "severity", "min_score", "source_mode", "q", "latest_only",
        "include_dismissed", "sort", "limit", "offset",
    ]:
        assert required_filter in f_params, f"Missing filter '{required_filter}' in /findings"

    # 3. Response statuses
    assert "201" in paths["/api/v1/brands"]["post"]["responses"]
    assert "201" in paths["/api/v1/brands/{brand_id}/assets"]["post"]["responses"]
    assert "202" in paths["/api/v1/scans"]["post"]["responses"]

    # 4. Critical schemas present in components
    schemas = openapi.get("components", {}).get("schemas", {})
    required_schemas = [
        "SourceHealth", "FindingListItem", "FindingDetailResponse",
        "FindingDecisionRequest", "ComparisonResponse", "ClearedListItem",
        "AuditEventResponse", "ScanDetailResponse", "BrandSummaryResponse",
        "AssetPrefillResponse", "OfficialAssetResponse",
    ]
    for s in required_schemas:
        assert s in schemas, f"Missing required component schema '{s}' in OpenAPI!"


def test_contract_enums_match_section_10() -> None:
    """All enum values and spellings must match Section 10 of ARCHITECTURE_API_CONTRACT.md exactly."""
    expected_enums = {
        ScanMode: ["LIVE", "DEMO"],
        SourceMode: ["LIVE", "CACHED", "SIMULATED"],
        SourceStatus: [
            "CONNECTED",
            "PARTIAL",
            "NOT_CONNECTED",
            "RATE_LIMITED",
            "ERROR",
        ],
        ScanStatus: [
            "QUEUED",
            "RUNNING",
            "COMPLETED",
            "COMPLETED_WITH_ERRORS",
            "FAILED",
        ],
        ScanStage: [
            "queued",
            "resolving_brand",
            "planning_queries",
            "fetching",
            "normalizing",
            "hashing_images",
            "assessing",
            "persisting",
            "completed",
            "failed",
        ],
        AssetType: ["IOS_APP", "ANDROID_APP", "SOCIAL_ACCOUNT"],
        Relationship: ["OFFICIAL", "AUTHORIZED_PARTNER"],
        VerificationMethod: [
            "OWNER_PROVIDED",
            "STORE_LOOKUP",
            "DOMAIN_VERIFIED_HANDLE",
        ],
        IdentityDecision: [
            "OFFICIAL_EXACT_MATCH",
            "OFFICIAL_PUBLISHER_MATCH",
            "AUTHORIZED_PARTNER_MATCH",
            "BENIGN_LOOKALIKE",
            "BELOW_THRESHOLD",
            "CANDIDATE_FOR_REVIEW",
        ],
        Severity: ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        FindingStatus: [
            "NEW",
            "IN_REVIEW",
            "CONFIRMED_SUSPICIOUS",
            "DISMISSED_FALSE_POSITIVE",
            "INCONCLUSIVE",
        ],
        EvidenceStatus: ["OBSERVED", "INFERRED", "UNAVAILABLE", "SIMULATED"],
        EvidenceGroup: ["NAME", "IDENTITY", "VISUAL", "CONTENT", "CONTEXT"],
        LookalikeTechnique: [
            "EXACT_NAME_REUSE",
            "HOMOGLYPH",
            "CHARACTER_SWAP",
            "OMISSION",
            "REPETITION",
            "KEYBOARD_ADJACENT",
            "ADDED_WORD",
            "SPACING",
            "SEPARATOR",
            "NONE",
        ],
        ProviderErrorCode: [
            "TIMEOUT",
            "RATE_LIMITED",
            "AUTH_REQUIRED",
            "PROVIDER_UNAVAILABLE",
            "NOT_CONFIGURED",
            "INVALID_RESPONSE",
            "BLOCKED_URL",
        ],
        ApiErrorCode: [
            "VALIDATION_ERROR",
            "NOT_FOUND",
            "CONFLICT",
            "SCAN_ALREADY_RUNNING",
            "MODE_NOT_ALLOWED",
            "RATE_LIMITED",
            "UNAUTHORIZED",
            "INTERNAL_ERROR",
        ],
        EvalLabel: ["IMPERSONATION", "BENIGN_NAMESAKE", "OFFICIAL"],
        EvalProvenance: ["REAL_CAPTURED", "SYNTHETIC"],
        EvalSplit: ["DEV", "HELDOUT"],
    }

    for enum_cls, expected_values in expected_enums.items():
        actual_values = [e.value for e in enum_cls]
        assert actual_values == expected_values, (
            f"Enum {enum_cls.__name__} mismatch! Expected {expected_values}, got {actual_values}"
        )
