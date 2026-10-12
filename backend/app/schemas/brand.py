"""Brand schemas for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.2
"""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

HOSTNAME_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$|"
    r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$"
)


def validate_hostname(domain: str) -> str:
    """Validate that domain is a valid hostname without scheme, path, or port."""
    cleaned = domain.strip().lower()
    if (
        "://" in cleaned
        or "/" in cleaned
        or "?" in cleaned
        or "#" in cleaned
        or ":" in cleaned
    ):
        raise ValueError(
            f"Domain '{domain}' must be a hostname only (no scheme, port, or path)."
        )
    if not HOSTNAME_REGEX.match(cleaned):
        raise ValueError(f"Domain '{domain}' is not a valid hostname.")
    return cleaned


class BrandCreate(BaseModel):
    """Payload for creating a brand."""

    name: str = Field(
        min_length=2, max_length=60, description="Brand name (2-60 chars)"
    )
    description: str | None = None
    official_domains: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list, max_length=12)
    distinctive_tokens: list[str] = Field(default_factory=list)
    generic_tokens_extra: list[str] = Field(default_factory=list)
    industry_category: str | None = None
    demo_brand: bool = False

    @field_validator("official_domains")
    @classmethod
    def validate_domains(cls, domains: list[str]) -> list[str]:
        return [validate_hostname(d) for d in domains]

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, keywords: list[str]) -> list[str]:
        if len(keywords) > 12:
            raise ValueError("Keywords list cannot exceed 12 items.")
        return keywords


class BrandUpdate(BaseModel):
    """Payload for updating permitted brand fields."""

    name: str | None = Field(default=None, min_length=2, max_length=60)
    description: str | None = None
    official_domains: list[str] | None = None
    keywords: list[str] | None = Field(default=None, max_length=12)
    distinctive_tokens: list[str] | None = None
    generic_tokens_extra: list[str] | None = None
    industry_category: str | None = None
    demo_brand: bool | None = None

    @field_validator("official_domains")
    @classmethod
    def validate_domains(cls, domains: list[str] | None) -> list[str] | None:
        if domains is not None:
            return [validate_hostname(d) for d in domains]
        return None

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, keywords: list[str] | None) -> list[str] | None:
        if keywords is not None and len(keywords) > 12:
            raise ValueError("Keywords list cannot exceed 12 items.")
        return keywords


class BrandResponse(BaseModel):
    """Brand detail response."""

    id: UUID
    name: str
    description: str | None = None
    official_domains: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    distinctive_tokens: list[str] = Field(default_factory=list)
    generic_tokens_extra: list[str] = Field(default_factory=list)
    industry_category: str | None = None
    demo_brand: bool = False
    created_at: datetime
    updated_at: datetime
    official_asset_count: int | None = None


class BrandSummaryResponse(BaseModel):
    """Overview aggregates for brand monitoring overview screen."""

    brand_id: UUID
    official_asset_count: int = 0
    last_scan: dict[str, Any] | None = None
    funnel: dict[str, int] = Field(
        default_factory=lambda: {
            "retrieved": 0,
            "deduplicated": 0,
            "official_cleared": 0,
            "not_relevant": 0,
            "benign_lookalike": 0,
            "below_threshold": 0,
            "findings": 0,
        }
    )
    findings_by_severity: dict[str, int] = Field(
        default_factory=lambda: {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    )
    findings_by_status: dict[str, int] = Field(
        default_factory=lambda: {
            "NEW": 0,
            "IN_REVIEW": 0,
            "CONFIRMED_SUSPICIOUS": 0,
            "DISMISSED_FALSE_POSITIVE": 0,
            "INCONCLUSIVE": 0,
        }
    )
    findings_by_platform: dict[str, int] = Field(default_factory=dict)
    cleared_by_decision: dict[str, int] = Field(
        default_factory=lambda: {
            "OFFICIAL_EXACT_MATCH": 0,
            "OFFICIAL_PUBLISHER_MATCH": 0,
            "AUTHORIZED_PARTNER_MATCH": 0,
            "BENIGN_LOOKALIKE": 0,
            "BELOW_THRESHOLD": 0,
        }
    )
    review_progress: dict[str, int] = Field(
        default_factory=lambda: {"reviewed": 0, "total": 0}
    )
    source_coverage: list[dict[str, Any]] = Field(default_factory=list)
    latest_evaluation: dict[str, Any] | None = None


class AuditEventResponse(BaseModel):
    """Audit log entry for brand changes, asset updates, and analyst decisions."""

    id: UUID
    brand_id: UUID
    actor_label: str = "analyst"
    event_type: str
    entity_type: str
    entity_id: UUID
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
