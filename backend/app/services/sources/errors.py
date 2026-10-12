"""Provider error definitions for external source adapters.

Owner: Person 3 (backend/app/services/sources/errors.py)
Reference: Contract Sections 5.5, 10, 11.3, 12
"""

from __future__ import annotations

from app.schemas import ProviderErrorCode


class ProviderError(Exception):
    """Exception raised when an external provider request fails.

    This exception carries a standardized ProviderErrorCode and a sanitized
    human-readable error message. The message must NEVER include query strings,
    raw request/response payloads, authentication tokens, or stack traces.

    Usage in Prefill (Section 11.3):
        When a store lookup fails due to a provider issue (such as a 429, 403,
        5xx, timeout, or invalid response) rather than a clean 'not found'
        (which returns None), lookup() raises ProviderError. Person 2's prefill
        endpoint handler catches this exception and returns an HTTP 200 response
        with `{"draft": null, "source_status": "...", "error_code": err.error_code}`,
        allowing the UI to show the failure reason gracefully and prompt for manual entry.
    """

    def __init__(self, error_code: ProviderErrorCode, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message

    def __repr__(self) -> str:
        return f"ProviderError(error_code={self.error_code.value!r}, message={self.message!r})"


class BlockedUrlError(ProviderError):
    """Exception raised when a user-supplied URL or identifier is blocked by security policy.

    Section 5.6 & 11.3:
    Raised during prefill parsing when a URL violates the allowlist, uses an invalid
    scheme, attempts SSRF/path traversal, or carries invalid identifiers.
    Person 2's prefill endpoint maps this exception to HTTP 422 VALIDATION_ERROR
    with ProviderErrorCode.BLOCKED_URL in the error details.
    """

    def __init__(
        self,
        message: str = "URL or identifier blocked by security policy",
        error_code: ProviderErrorCode = ProviderErrorCode.BLOCKED_URL,
    ) -> None:
        super().__init__(error_code=error_code, message=message)
