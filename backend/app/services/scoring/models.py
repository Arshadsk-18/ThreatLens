"""Scoring models, enums, and configuration for ThreatLens v3."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from backend.app.services.normalization.techniques import LookalikeTechnique
from backend.app.services.query_planner.models import (
    AssetType,
    IdentityDecision,
)


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvidenceStatus(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    UNAVAILABLE = "UNAVAILABLE"
    SIMULATED = "SIMULATED"


class EvidenceGroup(str, Enum):
    NAME = "NAME"
    IDENTITY = "IDENTITY"
    VISUAL = "VISUAL"
    CONTENT = "CONTENT"
    CONTEXT = "CONTEXT"


class SourceMode(str, Enum):
    LIVE = "LIVE"
    CACHED = "CACHED"
    SIMULATED = "SIMULATED"


class NormalizedCandidate(BaseModel):
    source_id: str = "apple_itunes"
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
    icon_hash: str | None = None
    canonical_url: str | None = None
    created_at_source: datetime | None = None
    followers: int | None = None
    following: int | None = None
    posts_count: int | None = None
    rating_count: int | None = None
    source_mode: SourceMode = SourceMode.LIVE
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    matched_queries: list[str] = Field(default_factory=list)


class SignalResult(BaseModel):
    signal: str
    group: EvidenceGroup
    value: float  # 0.0 - 1.0
    points: float
    max_points: float
    status: EvidenceStatus
    reason: str
    detail: dict[str, Any] = Field(default_factory=dict)


class AssessmentResult(BaseModel):
    identity_decision: IdentityDecision
    rule: str
    matched_official_asset_id: UUID | None = None
    risk_score: int | None = None
    severity: Severity | None = None
    evidence_coverage: float | None = None
    corroborating_groups: list[EvidenceGroup] = Field(default_factory=list)
    gates_applied: list[str] = Field(default_factory=list)
    breakdown: list[SignalResult] = Field(default_factory=list)
    technique: LookalikeTechnique = LookalikeTechnique.NONE
    nearest_official_asset_id: UUID | None = None
    explanation: str = ""
    scoring_version: str = "3.0.0"
    relevant: bool = True  # False when G1 failed

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class ScoringConfig(BaseModel):
    scoring_version: str = "3.0.0"
    relevance_threshold: float = 0.60
    review_threshold: int = 25
    evidence_coverage_min: float = 0.50
    category_synonyms: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "finance": ["banking", "financial", "fintech", "payments"],
            "banking": ["finance", "financial", "fintech", "payments"],
            "shopping": ["e-commerce", "retail", "marketplace"],
            "food & drink": ["food", "restaurants", "dining", "coffee"],
        }
    )
