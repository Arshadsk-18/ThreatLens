"""Scoring and assessment schemas for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 8, 12
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import (
    EvidenceGroup,
    EvidenceStatus,
    IdentityDecision,
    LookalikeTechnique,
    Severity,
)


class ScoringConfig(BaseModel):
    """Runtime configuration for scoring thresholds and gate rules."""

    scoring_version: str = "3.0.0"
    relevance_threshold: float = 0.60
    review_threshold: int = 25
    g4_low_content_overlap_threshold: float = 0.20
    g2_corroborating_groups_min: int = 2
    g3_evidence_coverage_min: float = 0.50
    category_synonyms: dict[str, list[str]] = Field(default_factory=dict)


class SignalResult(BaseModel):
    """Evaluation result for an individual risk signal."""

    signal: str
    group: EvidenceGroup
    value: float
    points: float
    max_points: float
    status: EvidenceStatus
    reason: str
    detail: dict[str, Any] = Field(default_factory=dict)


class AssessmentResult(BaseModel):
    """Pure output of assessing a candidate asset against brand context."""

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
    explanation: str = ""
    scoring_version: str = "3.0.0"
    relevant: bool = True

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)  # False when G1 relevance gate fails (not persisted)
