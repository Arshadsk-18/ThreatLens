"""Health and readiness schemas for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.1
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Payload returned by GET /api/v1/health."""

    status: str = "ok"
    service: str = "threatlens-api"
    version: str = "3.0.0"
    contract_version: str = "3.0.0"


class ReadyChecks(BaseModel):
    """Subsystem readiness checks dictionary."""

    database: str = "ok"
    config: str = "ok"


class ReadyResponse(BaseModel):
    """Payload returned by GET /api/v1/ready."""

    ready: bool = True
    checks: dict[str, str] = Field(
        default_factory=lambda: {"database": "ok", "config": "ok"}
    )
