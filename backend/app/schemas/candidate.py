"""Candidate and query models for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 12
Owner: Person 2 (Consumed by Persons 3, 4, 5)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import (
    AssetType,
    ProviderErrorCode,
    SourceMode,
    SourceStatus,
)


class NormalizedCandidate(BaseModel):
    """Normalized representation of an external observed asset."""

    source_id: str
    platform: str
    asset_type: AssetType
    stable_identifier: str
    secondary_identifiers: dict[str, str] = Field(default_factory=dict)
    display_name: str
    handle: str | None = None
    publisher_name: str | None = None
    developer_id: str | None = None
    description: str | None = None
    category: str | None = None
    external_links: list[str] = Field(default_factory=list)
    icon_url: str | None = None
    icon_hash: str | None = None  # filled by image_fetch before assess()
    canonical_url: str | None = None
    created_at_source: datetime | None = None
    followers: int | None = None
    following: int | None = None
    posts_count: int | None = None
    rating_count: int | None = None
    source_mode: SourceMode
    retrieved_at: datetime
    matched_queries: list[str] = Field(default_factory=list)


class PlannedQuery(BaseModel):
    """Individual query planned by the query planner."""

    term: str
    kind: str  # BASE | SPACING | SEPARATOR | ADDED_WORD | DISTINCTIVE
    priority: int


class QueryPlan(BaseModel):
    """Targeted search plan for a brand across sources."""

    brand_id: UUID
    queries: list[PlannedQuery] = Field(default_factory=list)


class SourceResult(BaseModel):
    """Aggregated output from an external source adapter."""

    source_id: str
    status: SourceStatus
    source_mode: SourceMode | None = None
    retrieved_at: datetime | None = None
    candidates: list[NormalizedCandidate] = Field(default_factory=list)
    queries_executed: int = 0
    cache_hit_count: int = 0
    error_code: ProviderErrorCode | None = None
    message: str = ""
    duration_ms: int = 0
