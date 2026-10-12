"""Source status and health schemas for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 11.1, 12
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import AssetType, SourceMode, SourceStatus


class SourceHealth(BaseModel):
    """Health check output and coverage status of an external provider source."""

    source_id: str
    display_name: str
    platform: str
    asset_types: list[AssetType] = Field(default_factory=list)
    status: SourceStatus
    supported_modes: list[SourceMode] = Field(default_factory=list)
    default_mode: SourceMode | None = None
    last_checked_at: datetime | None = None
    rate_limit_note: str | None = None
    message: str = ""


# Alias for GET /sources/status response items
SourceStatusEntry = SourceHealth
