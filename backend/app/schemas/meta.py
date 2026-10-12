"""Metadata schema for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.1
"""

from typing import Any

from pydantic import BaseModel, Field


class MetaResponse(BaseModel):
    """Payload returned by GET /api/v1/meta."""

    scoring_version: str = "3.0.0"
    contract_version: str = "3.0.0"
    enums: dict[str, list[str]] = Field(default_factory=dict)
    thresholds: dict[str, Any] = Field(default_factory=dict)
    signal_tables: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    supported_platforms: list[dict[str, Any]] = Field(default_factory=list)
    supported_asset_types: list[str] = Field(default_factory=list)
