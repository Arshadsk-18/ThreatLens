"""Scan request and response schemas for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.4
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import (
    AssetType,
    ProviderErrorCode,
    ScanMode,
    ScanStage,
    ScanStatus,
    SourceMode,
    SourceStatus,
)


class ScanOptions(BaseModel):
    """Execution options configuration for a scan."""

    asset_types: list[AssetType] = Field(
        default_factory=lambda: [AssetType.IOS_APP, AssetType.SOCIAL_ACCOUNT]
    )
    source_ids: list[str] = Field(
        default_factory=lambda: ["apple_itunes", "bluesky_public"]
    )
    query_limit_per_source: int = Field(default=25, ge=1, le=50)
    include_icon_similarity: bool = True
    force_refresh: bool = False
    allow_stale_cache: bool = False


class ScanStartRequest(BaseModel):
    """Payload to trigger a new scan."""

    brand_id: UUID
    mode: ScanMode = ScanMode.LIVE
    asset_types: list[AssetType] = Field(
        default_factory=lambda: [AssetType.IOS_APP, AssetType.SOCIAL_ACCOUNT]
    )
    source_ids: list[str] = Field(
        default_factory=lambda: ["apple_itunes", "bluesky_public"]
    )
    query_limit_per_source: int = Field(default=25, ge=1, le=50)
    include_icon_similarity: bool = True
    force_refresh: bool = False
    allow_stale_cache: bool = False


class ScanStartResponse(BaseModel):
    """Response returned immediately upon queuing a scan (HTTP 202 Accepted)."""

    id: UUID
    brand_id: UUID
    mode: ScanMode
    status: ScanStatus = ScanStatus.QUEUED
    stage: ScanStage = ScanStage.queued
    progress_percent: int = 0
    created_at: datetime


class SourceOutcome(BaseModel):
    """Outcome and query metrics for an individual source provider."""

    source_id: str
    status: SourceStatus
    source_mode: SourceMode | None = None
    queries_planned: int = 0
    queries_executed: int = 0
    candidate_count: int = 0
    cache_hit_count: int = 0
    error_code: ProviderErrorCode | None = None
    message: str = ""
    retrieved_at: datetime | None = None
    duration_ms: int = 0


class ScanFunnel(BaseModel):
    """Funnel counters enforcing deduplicated invariant."""

    retrieved: int = 0
    deduplicated: int = 0
    official_cleared: int = 0
    not_relevant: int = 0
    benign_lookalike: int = 0
    below_threshold: int = 0
    findings: int = 0


class ScanEvent(BaseModel):
    """Log event emitted during scan pipeline progression."""

    at: datetime
    stage: str
    level: str = "INFO"
    message: str
    source_id: str | None = None


class ScanDetailResponse(BaseModel):
    """Detailed scan status and outcomes polled by frontend."""

    id: UUID
    brand_id: UUID
    mode: ScanMode
    status: ScanStatus
    stage: ScanStage
    progress_percent: int
    options: ScanOptions
    source_outcomes: list[SourceOutcome] = Field(default_factory=list)
    funnel: ScanFunnel = Field(default_factory=ScanFunnel)
    findings_by_severity: dict[str, int] = Field(
        default_factory=lambda: {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    )
    events: list[ScanEvent] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
