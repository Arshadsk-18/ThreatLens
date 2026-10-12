"""Finding and cleared item schemas for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.5
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.enums import (
    AssetType,
    EvidenceGroup,
    EvidenceStatus,
    FindingStatus,
    IdentityDecision,
    LookalikeTechnique,
    Severity,
    SourceMode,
)
from app.schemas.scoring import SignalResult


class CandidateSummary(BaseModel):
    """External observed candidate summary for list views."""

    platform: str
    asset_type: AssetType
    stable_identifier: str
    display_name: str
    handle: str | None = None
    publisher_name: str | None = None
    icon_url: str | None = None
    canonical_url: str | None = None


class TopSignal(BaseModel):
    """Top highlighted signal explaining why finding was surfaced."""

    signal: str
    points: float
    max_points: float
    reason: str


class FindingListItem(BaseModel):
    """Candidate for review item listed in findings queue."""

    id: UUID
    brand_id: UUID
    scan_id: UUID
    candidate: CandidateSummary
    risk_score: int
    severity: Severity
    evidence_coverage: float
    technique: LookalikeTechnique
    top_signals: list[TopSignal] = Field(default_factory=list)
    status: FindingStatus = FindingStatus.NEW
    source_mode: SourceMode
    observed_at: datetime
    changed_since_decision: bool = False


class ClearedCandidateSummary(BaseModel):
    """External asset summary for cleared views."""

    platform: str
    asset_type: AssetType
    stable_identifier: str
    display_name: str
    publisher_name: str | None = None
    icon_url: str | None = None


class ClearedListItem(BaseModel):
    """Candidate cleared by exact ID, publisher ID, partner, or benign gate."""

    id: UUID
    scan_id: UUID
    candidate: ClearedCandidateSummary
    decision: IdentityDecision
    rule: str
    matched_official_asset_id: UUID | None = None
    explanation: str
    risk_score: int | None = None
    source_mode: SourceMode
    observed_at: datetime


class FindingDetailCandidate(CandidateSummary):
    """Candidate details for finding view."""

    description: str | None = None
    category: str | None = None
    external_links: list[str] = Field(default_factory=list)
    created_at_source: datetime | None = None
    followers: int | None = None
    rating_count: int | None = None


class IdentityGuardResult(BaseModel):
    """IdentityGuard outcome recorded with assessment."""

    decision: IdentityDecision
    rule: str
    matched_official_asset_id: UUID | None = None
    explanation: str


class EvidenceItem(BaseModel):
    """Individual item of observable evidence."""

    id: UUID
    evidence_type: str
    source_id: str
    status: EvidenceStatus
    observed_at: datetime
    field_name: str | None = None
    observed_value: Any = None
    source_url: str | None = None
    notes: str | None = None


class DecisionHistoryItem(BaseModel):
    """Historical record of an analyst decision on a finding."""

    previous_status: FindingStatus | str
    new_status: FindingStatus | str
    decision_reason: str
    notes: str | None = None
    actor_label: str = "analyst"
    created_at: datetime


class FindingDecisionRequest(BaseModel):
    """Payload for PATCH /findings/{id} analyst decision."""

    status: FindingStatus
    decision_reason: str | None = None
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _remap_new_status(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "new_status" in data and "status" not in data:
                data["status"] = data["new_status"]
        return data

    @model_validator(mode="after")
    def validate_reason(self) -> "FindingDecisionRequest":
        if self.status in {
            FindingStatus.DISMISSED_FALSE_POSITIVE,
            FindingStatus.CONFIRMED_SUSPICIOUS,
        } and (not self.decision_reason or not self.decision_reason.strip()):
            raise ValueError(
                f"decision_reason is required for status '{self.status.value}'."
            )
        return self


class FindingDetailResponse(BaseModel):
    """Comprehensive finding detail payload for GET /findings/{id} and PATCH /findings/{id}."""

    id: UUID
    brand_id: UUID
    scan_id: UUID
    candidate: FindingDetailCandidate
    identity_guard: IdentityGuardResult
    risk_score: int
    severity: Severity
    evidence_coverage: float
    technique: LookalikeTechnique = LookalikeTechnique.NONE
    top_signals: list[TopSignal] = Field(default_factory=list)
    corroborating_groups: list[EvidenceGroup] = Field(default_factory=list)
    gates_applied: list[str] = Field(default_factory=list)
    score_breakdown: list[SignalResult] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    explanation: str = ""
    limitations: list[str] = Field(default_factory=list)
    scoring_version: str = "3.0.0"
    source_mode: SourceMode
    status: FindingStatus = FindingStatus.NEW
    decision_history: list[DecisionHistoryItem] = Field(default_factory=list)
    created_at: datetime
    observed_at: datetime | None = None
    changed_since_decision: bool = False
