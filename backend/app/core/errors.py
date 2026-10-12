"""Custom exceptions and error mapping for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 10
"""

from typing import Any

from app.schemas.enums import ApiErrorCode
from app.schemas.error import ErrorDetail

API_ERROR_HTTP_MAPPING: dict[ApiErrorCode, int] = {
    ApiErrorCode.VALIDATION_ERROR: 422,
    ApiErrorCode.NOT_FOUND: 404,
    ApiErrorCode.CONFLICT: 409,
    ApiErrorCode.SCAN_ALREADY_RUNNING: 409,
    ApiErrorCode.MODE_NOT_ALLOWED: 422,
    ApiErrorCode.RATE_LIMITED: 429,
    ApiErrorCode.UNAUTHORIZED: 401,
    ApiErrorCode.INTERNAL_ERROR: 500,
}


class AppException(Exception):
    """Base application exception mapped to standard error envelope."""

    def __init__(
        self,
        code: ApiErrorCode,
        message: str,
        details: list[ErrorDetail] | list[dict[str, Any]] | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        if details:
            self.details = [
                d if isinstance(d, ErrorDetail) else ErrorDetail(**d) for d in details
            ]
        else:
            self.details = []
        self.status_code = status_code or API_ERROR_HTTP_MAPPING.get(code, 500)
        self.headers = headers or {}
        super().__init__(message)


class NotFoundException(AppException):
    """Resource not found (404)."""

    def __init__(
        self,
        message: str = "Resource not found.",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(
            code=ApiErrorCode.NOT_FOUND,
            message=message,
            details=details,
            status_code=404,
        )


class ConflictException(AppException):
    """Resource conflict (409)."""

    def __init__(
        self,
        message: str = "Resource conflict.",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(
            code=ApiErrorCode.CONFLICT,
            message=message,
            details=details,
            status_code=409,
        )


class ScanAlreadyRunningException(AppException):
    """Another scan is already running for this brand (409)."""

    def __init__(
        self,
        message: str = "A scan is already running for this brand.",
    ) -> None:
        super().__init__(
            code=ApiErrorCode.SCAN_ALREADY_RUNNING,
            message=message,
            status_code=409,
        )


class ValidationException(AppException):
    """Validation failed (422 or 400)."""

    def __init__(
        self,
        message: str = "Invalid fields.",
        details: list[ErrorDetail] | list[dict[str, Any]] | None = None,
        status_code: int = 422,
    ) -> None:
        super().__init__(
            code=ApiErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
            status_code=status_code,
        )


class ModeNotAllowedException(AppException):
    """Mode or source combination not permitted (422)."""

    def __init__(
        self,
        message: str = "Requested scan mode is not allowed with selected sources.",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(
            code=ApiErrorCode.MODE_NOT_ALLOWED,
            message=message,
            details=details,
            status_code=422,
        )


class RateLimitedException(AppException):
    """Demo API rate limit reached (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please retry later.",
        retry_after: int = 60,
    ) -> None:
        headers = {"Retry-After": str(retry_after)}
        super().__init__(
            code=ApiErrorCode.RATE_LIMITED,
            message=message,
            status_code=429,
            headers=headers,
        )


class UnauthorizedException(AppException):
    """Missing or invalid credentials (401)."""

    def __init__(
        self,
        message: str = "Authentication required.",
    ) -> None:
        super().__init__(
            code=ApiErrorCode.UNAUTHORIZED,
            message=message,
            status_code=401,
        )


class InternalErrorException(AppException):
    """Internal server error (500)."""

    def __init__(
        self,
        message: str = "An internal server error occurred.",
    ) -> None:
        super().__init__(
            code=ApiErrorCode.INTERNAL_ERROR,
            message=message,
            status_code=500,
        )
