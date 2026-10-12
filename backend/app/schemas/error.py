"""Error envelope schemas for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 10
"""

from pydantic import BaseModel, Field

from app.schemas.enums import ApiErrorCode


class ErrorDetail(BaseModel):
    """Field-level error specification."""

    field: str | None = None
    issue: str


class ErrorBody(BaseModel):
    """Structured error payload enclosed inside ErrorEnvelope."""

    code: ApiErrorCode
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: str


class ErrorEnvelope(BaseModel):
    """Top-level error response envelope for all API errors."""

    error: ErrorBody
