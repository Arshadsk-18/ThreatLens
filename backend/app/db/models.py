"""SQLAlchemy 2.0 models for ThreatLens v3 matching Section 9 data model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship

from .base import Base, UTCDateTime, generate_uuid, utc_now


class Brand(Base):
    """Brand profile and registered metadata."""

    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_domains: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    keywords: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    distinctive_tokens: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    generic_tokens_extra: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    industry_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    demo_brand: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    official_assets: Mapped[list[OfficialAsset]] = orm_relationship(
        "OfficialAsset", back_populates="brand", cascade="all, delete-orphan"
    )
    scans: Mapped[list[Scan]] = orm_relationship(
        "Scan", back_populates="brand", cascade="all, delete-orphan"
    )
    candidate_assets: Mapped[list[CandidateAsset]] = orm_relationship(
        "CandidateAsset", back_populates="brand", cascade="all, delete-orphan"
    )


class OfficialAsset(Base):
    """Legitimate official asset registered by a brand."""

    __tablename__ = "official_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False
    )
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    stable_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    secondary_identifiers: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    developer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publisher_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    icon_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)
    verification_method: Mapped[str] = mapped_column(String(50), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trust_publisher: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    brand: Mapped[Brand] = orm_relationship("Brand", back_populates="official_assets")

    __table_args__ = (
        UniqueConstraint(
            "brand_id",
            "platform",
            "stable_identifier",
            name="uq_official_assets_brand_platform_stable_id",
        ),
        Index("ix_official_assets_brand_id_platform", "brand_id", "platform"),
        Index("ix_official_assets_brand_id", "brand_id"),
    )


class Scan(Base):
    """Scan job execution record and outcomes."""

    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    options: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_outcomes: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    funnel: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    findings_by_severity: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    events: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )  # capped at 200
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )
    started_at: Mapped[UTCDateTime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[UTCDateTime | None] = mapped_column(UTCDateTime, nullable=True)

    # Relationships
    brand: Mapped[Brand] = orm_relationship("Brand", back_populates="scans")
    assessments: Mapped[list[Assessment]] = orm_relationship(
        "Assessment", back_populates="scan", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_scans_brand_id_status", "brand_id", "status"),
        Index("ix_scans_brand_id", "brand_id"),
        Index("ix_scans_status", "status"),
    )


class CandidateAsset(Base):
    """Discovered candidate asset across platforms with decision memory."""

    __tablename__ = "candidate_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    stable_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    secondary_identifiers: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publisher_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    developer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_links: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    icon_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    icon_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at_source: Mapped[UTCDateTime | None] = mapped_column(
        UTCDateTime, nullable=True
    )
    followers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    following: Mapped[int | None] = mapped_column(Integer, nullable=True)
    posts_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_source_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    analyst_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="NEW"
    )
    analyst_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )
    last_seen_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )
    last_scan_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    brand: Mapped[Brand] = orm_relationship("Brand", back_populates="candidate_assets")
    assessments: Mapped[list[Assessment]] = orm_relationship(
        "Assessment", back_populates="candidate_asset", cascade="all, delete-orphan"
    )
    analyst_decisions: Mapped[list[AnalystDecision]] = orm_relationship(
        "AnalystDecision",
        back_populates="candidate_asset",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "brand_id",
            "platform",
            "stable_identifier",
            name="uq_candidate_assets_brand_platform_stable_id",
        ),
        Index("ix_candidate_assets_brand_id_platform", "brand_id", "platform"),
        Index("ix_candidate_assets_brand_id_status", "brand_id", "analyst_status"),
        Index("ix_candidate_assets_last_scan_id", "last_scan_id"),
        Index("ix_candidate_assets_brand_id", "brand_id"),
    )


class Assessment(Base):
    """Detection assessment result for a candidate within a scan."""

    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    scan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False
    )
    candidate_asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    identity_decision: Mapped[str] = mapped_column(String(50), nullable=False)
    rule: Mapped[str] = mapped_column(String(100), nullable=False)
    matched_official_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("official_assets.id", ondelete="SET NULL"), nullable=True
    )
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    evidence_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    corroborating_groups: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    gates_applied: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    score_breakdown: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    technique: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    source_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(50), nullable=False)
    nearest_official_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("official_assets.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )

    # Relationships
    scan: Mapped[Scan] = orm_relationship("Scan", back_populates="assessments")
    candidate_asset: Mapped[CandidateAsset] = orm_relationship(
        "CandidateAsset", back_populates="assessments"
    )
    evidence_items: Mapped[list[Evidence]] = orm_relationship(
        "Evidence", back_populates="assessment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_assessments_scan_id", "scan_id"),
        Index("ix_assessments_candidate_asset_id", "candidate_asset_id"),
        Index("ix_assessments_brand_id", "brand_id"),
    )


class Evidence(Base):
    """Specific observable evidence item attached to an assessment."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    candidate_asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    scan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    observed_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    observed_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    assessment: Mapped[Assessment] = orm_relationship(
        "Assessment", back_populates="evidence_items"
    )

    __table_args__ = (
        Index("ix_evidence_scan_id", "scan_id"),
        Index("ix_evidence_candidate_asset_id", "candidate_asset_id"),
        Index("ix_evidence_assessment_id", "assessment_id"),
    )


class AnalystDecision(Base):
    """Human analyst review decision on a candidate."""

    __tablename__ = "analyst_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    assessment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True
    )
    previous_status: Mapped[str] = mapped_column(String(50), nullable=False)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_label: Mapped[str] = mapped_column(
        String(100), nullable=False, default="analyst"
    )
    created_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )

    # Relationships
    candidate_asset: Mapped[CandidateAsset] = orm_relationship(
        "CandidateAsset", back_populates="analyst_decisions"
    )

    __table_args__ = (
        Index("ix_analyst_decisions_candidate_asset_id", "candidate_asset_id"),
        Index("ix_analyst_decisions_assessment_id", "assessment_id"),
    )


class AuditEvent(Base):
    """Audit log trail of security-relevant and administrative actions."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False
    )
    actor_label: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )

    __table_args__ = (Index("ix_audit_events_brand_id", "brand_id"),)


class ResponseCache(Base):
    """External API response cache table."""

    __tablename__ = "response_cache"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(50), nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    retrieved_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)


class EvaluationRun(Base):
    """Evaluation harness offline run results."""

    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    dataset_id: Mapped[str] = mapped_column(String(100), nullable=False)
    split: Mapped[str] = mapped_column(String(50), nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[UTCDateTime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )
