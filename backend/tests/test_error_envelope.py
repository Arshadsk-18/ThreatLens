"""Tests for error envelope, X-Request-ID, and ApiErrorCode HTTP mapping.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 10
"""

import uuid

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.core.errors import (
    API_ERROR_HTTP_MAPPING,
    ConflictException,
    ModeNotAllowedException,
    NotFoundException,
    RateLimitedException,
    ScanAlreadyRunningException,
    UnauthorizedException,
    ValidationException,
)
from app.main import create_app
from app.schemas.enums import ApiErrorCode
from app.schemas.error import ErrorDetail


def test_api_error_http_mapping_values() -> None:
    """Validate exact HTTP status mapping defined in Section 10."""
    assert API_ERROR_HTTP_MAPPING[ApiErrorCode.VALIDATION_ERROR] == 422
    assert API_ERROR_HTTP_MAPPING[ApiErrorCode.NOT_FOUND] == 404
    assert API_ERROR_HTTP_MAPPING[ApiErrorCode.CONFLICT] == 409
    assert API_ERROR_HTTP_MAPPING[ApiErrorCode.SCAN_ALREADY_RUNNING] == 409
    assert API_ERROR_HTTP_MAPPING[ApiErrorCode.MODE_NOT_ALLOWED] == 422
    assert API_ERROR_HTTP_MAPPING[ApiErrorCode.RATE_LIMITED] == 429
    assert API_ERROR_HTTP_MAPPING[ApiErrorCode.UNAUTHORIZED] == 401
    assert API_ERROR_HTTP_MAPPING[ApiErrorCode.INTERNAL_ERROR] == 500


def test_404_returns_contract_error_envelope(client: TestClient) -> None:
    """Non-existent path must return 404 with standard error envelope."""
    response = client.get("/api/v1/nonexistent-route")
    assert response.status_code == 404
    assert "X-Request-ID" in response.headers

    data = response.json()
    assert "error" in data
    error = data["error"]
    assert error["code"] == ApiErrorCode.NOT_FOUND.value
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert isinstance(error["details"], list)


def test_custom_app_exceptions_in_envelope() -> None:
    """Custom exceptions raise and serialize into standard ErrorEnvelope with mapped status."""
    test_router = APIRouter()

    @test_router.get("/test/not-found")
    def route_not_found():
        raise NotFoundException("Brand does not exist.")

    @test_router.get("/test/conflict")
    def route_conflict():
        raise ConflictException("Duplicate asset registered.")

    @test_router.get("/test/scan-running")
    def route_scan_running():
        raise ScanAlreadyRunningException()

    @test_router.get("/test/validation-error")
    def route_validation_error():
        raise ValidationException(
            "Invalid fields.",
            details=[
                ErrorDetail(
                    field="stable_identifier",
                    issue="Must be numeric for apple_app_store",
                )
            ],
        )

    @test_router.get("/test/mode-not-allowed")
    def route_mode_not_allowed():
        raise ModeNotAllowedException()

    @test_router.get("/test/rate-limited")
    def route_rate_limited():
        raise RateLimitedException(retry_after=45)

    @test_router.get("/test/unauthorized")
    def route_unauthorized():
        raise UnauthorizedException()

    app = create_app()
    app.include_router(test_router)
    test_client = TestClient(app)

    # 404 Not Found
    r = test_client.get("/test/not-found")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == ApiErrorCode.NOT_FOUND.value
    assert r.json()["error"]["message"] == "Brand does not exist."

    # 409 Conflict
    r = test_client.get("/test/conflict")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == ApiErrorCode.CONFLICT.value

    # 409 Scan Already Running
    r = test_client.get("/test/scan-running")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == ApiErrorCode.SCAN_ALREADY_RUNNING.value

    # 422 Validation Error
    r = test_client.get("/test/validation-error")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == ApiErrorCode.VALIDATION_ERROR.value
    assert len(r.json()["error"]["details"]) == 1
    assert r.json()["error"]["details"][0]["field"] == "stable_identifier"
    assert (
        r.json()["error"]["details"][0]["issue"]
        == "Must be numeric for apple_app_store"
    )

    # 422 Mode Not Allowed
    r = test_client.get("/test/mode-not-allowed")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == ApiErrorCode.MODE_NOT_ALLOWED.value

    # 429 Rate Limited with Retry-After
    r = test_client.get("/test/rate-limited")
    assert r.status_code == 429
    assert r.json()["error"]["code"] == ApiErrorCode.RATE_LIMITED.value
    assert r.headers.get("Retry-After") == "45"

    # 401 Unauthorized
    r = test_client.get("/test/unauthorized")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == ApiErrorCode.UNAUTHORIZED.value


def test_x_request_id_header_propagation(client: TestClient) -> None:
    """Client-provided X-Request-ID must be echoed in response and error envelope."""
    custom_rid = str(uuid.uuid4())
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_rid})
    assert response.headers["X-Request-ID"] == custom_rid

    # And for an error response
    err_response = client.get(
        "/api/v1/nonexistent", headers={"X-Request-ID": custom_rid}
    )
    assert err_response.headers["X-Request-ID"] == custom_rid
    assert err_response.json()["error"]["request_id"] == custom_rid
