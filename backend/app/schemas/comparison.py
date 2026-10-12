"""Comparison schemas for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 11.5, 12
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class NameDiffSegment(BaseModel):
    """Segment in a character-level name difference breakdown."""

    text: str
    changed: bool


class NonAsciiChar(BaseModel):
    """Observed non-ASCII character with unicode codepoint."""

    char: str
    codepoint: str
    index: int


class FieldComparison(BaseModel):
    """Side-by-side comparison of an attribute between official and candidate."""

    field: str
    official_value: Any = None
    candidate_value: Any = None
    similarity: float | None = None
    name_diff: list[NameDiffSegment] | None = None
    non_ascii_chars: list[NonAsciiChar] | None = None
    detail: dict[str, Any] | None = None


class ComparisonAssetSummary(BaseModel):
    """Summary of asset fields shown in Evidence Compare view."""

    asset_id: UUID | None = None
    display_name: str
    stable_identifier: str
    publisher_name: str | None = None
    developer_id: str | None = None
    category: str | None = None
    icon_url: str | None = None
    canonical_url: str | None = None


class ComparisonResponse(BaseModel):
    """Response payload for GET /findings/{id}/comparison."""

    finding_id: UUID
    nearest_official_asset_id: UUID | None = None
    official_asset: ComparisonAssetSummary
    candidate_asset: ComparisonAssetSummary
    comparisons: list[FieldComparison] = Field(default_factory=list)
    disclaimer: str = (
        "Similarity indicates a candidate for review, not proof of malicious intent."
    )
