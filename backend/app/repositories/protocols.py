"""Repository protocols, domain exceptions, and data transfer types for ThreatLens."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, Protocol, TypeVar


class DomainValidationError(Exception):
    """Raised when repository input violates domain constraints (maps to VALIDATION_ERROR)."""


class EntityNotFoundError(Exception):
    """Raised when an expected entity does not exist (maps to NOT_FOUND)."""


def compute_content_hash(
    display_name: str | None,
    publisher_name: str | None,
    description: str | None,
    icon_hash: str | None,
) -> str:
    """Compute sha256 content_hash from (display_name, publisher_name, description, icon_hash) only."""
    parts = [
        display_name or "",
        publisher_name or "",
        description or "",
        icon_hash or "",
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    """Standard pagination wrapper matching Section 10 API conventions."""

    items: list[T]
    total: int
    limit: int
    offset: int


@dataclass
class CachedResponse:
    """Cached response item matching response_cache table."""

    key: str
    source_id: str
    request: dict[str, Any]
    response: dict[str, Any]
    retrieved_at: datetime
    ttl_seconds: int


@dataclass
class AuditEventRecord:
    """Audit event record matching audit_events table."""

    id: str
    brand_id: str
    actor_label: str
    event_type: str
    entity_type: str
    entity_id: str
    details: dict[str, Any]
    created_at: datetime


@dataclass
class FindingRecord:
    """Finding item representing candidate for review."""

    id: str
    brand_id: str
    scan_id: str
    candidate: dict[str, Any]
    risk_score: int | None
    severity: str | None
    evidence_coverage: float | None
    technique: str
    top_signals: list[dict[str, Any]] = field(default_factory=list)
    status: str = "NEW"
    source_mode: str = "LIVE"
    observed_at: datetime | None = None
    changed_since_decision: bool = False
    candidate_asset_id: str | None = None


@dataclass
class ClearedRecord:
    """Cleared item representing candidates cleared by identity or below threshold."""

    id: str
    scan_id: str
    candidate: dict[str, Any]
    decision: str
    rule: str
    matched_official_asset_id: str | None
    explanation: str
    risk_score: int | None
    source_mode: str
    observed_at: datetime | None = None
    candidate_asset_id: str | None = None


class BrandRepo(Protocol):
    """Protocol for brand profile persistence."""

    def create(self, brand_data: dict[str, Any]) -> dict[str, Any]: ...
    def get(self, brand_id: str) -> dict[str, Any] | None: ...
    def list(self, limit: int = 20, offset: int = 0) -> Page[dict[str, Any]]: ...
    def update(
        self, brand_id: str, update_data: dict[str, Any]
    ) -> dict[str, Any] | None: ...


class AssetRepo(Protocol):
    """Protocol for official asset registry persistence."""

    def create(
        self, asset_data: dict[str, Any], actor_label: str = "system"
    ) -> dict[str, Any]: ...
    def get(self, asset_id: str) -> dict[str, Any] | None: ...
    def list_by_brand(
        self,
        brand_id: str,
        asset_type: str | None = None,
        relationship: str | None = None,
        is_verified: bool | None = None,
        is_active: bool | None = None,
    ) -> list[dict[str, Any]]: ...
    def update(
        self, asset_id: str, update_data: dict[str, Any], actor_label: str = "system"
    ) -> dict[str, Any] | None: ...


class ScanRepo(Protocol):
    """Protocol for scan execution and lifecycle persistence."""

    def create(self, scan_data: dict[str, Any]) -> dict[str, Any]: ...
    def get(self, scan_id: str) -> dict[str, Any] | None: ...
    def list(
        self, brand_id: str, limit: int = 20, offset: int = 0
    ) -> Page[dict[str, Any]]: ...
    def update_progress(
        self, scan_id: str, stage: str, progress_percent: int
    ) -> dict[str, Any] | None: ...
    def append_event(self, scan_id: str, event_data: dict[str, Any]) -> None: ...
    def finish(
        self,
        scan_id: str,
        status: str,
        source_outcomes: list[Any],
        funnel: dict[str, Any],
        findings_by_severity: dict[str, int],
        error_message: str | None = None,
    ) -> dict[str, Any] | None: ...


class CandidateRepo(Protocol):
    """Protocol for candidate asset persistence with race-safe upsert and decision memory."""

    def upsert(self, candidate: Any, brand_id: str, scan_id: str) -> dict[str, Any]: ...
    def get(self, candidate_id: str) -> dict[str, Any] | None: ...
    def get_by_stable_id(
        self, brand_id: str, platform: str, stable_identifier: str
    ) -> dict[str, Any] | None: ...


class AssessmentRepo(Protocol):
    """Protocol for assessment results, findings queue, and cleared items."""

    def save(
        self,
        scan_id: str,
        candidate_id: str,
        result: Any,
        evidence: Sequence[Any],
        brand_id: str | None = None,
    ) -> str: ...
    def list_findings(
        self,
        brand_id: str | None = None,
        scan_id: str | None = None,
        status: str | None = None,
        asset_type: str | None = None,
        platform: str | None = None,
        severity: str | None = None,
        min_score: int | None = None,
        source_mode: str | None = None,
        q: str | None = None,
        latest_only: bool = True,
        include_dismissed: bool = False,
        sort: str = "score_desc",
        limit: int = 20,
        offset: int = 0,
    ) -> Page[FindingRecord]: ...
    def list_cleared(
        self,
        brand_id: str | None = None,
        decision: str | None = None,
        scan_id: str | None = None,
        platform: str | None = None,
        q: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Page[ClearedRecord]: ...


class DecisionRepo(Protocol):
    """Protocol for analyst decision recording with atomic status, decision, and audit logging."""

    def record(
        self,
        candidate_id: str,
        assessment_id: str | None,
        new_status: str,
        decision_reason: str,
        notes: str | None = None,
        actor_label: str = "analyst",
    ) -> dict[str, Any]: ...
    def list_by_candidate(self, candidate_id: str) -> list[dict[str, Any]]: ...


class AuditRepo(Protocol):
    """Protocol for recording and listing security audit events."""

    def log(
        self,
        brand_id: str,
        actor_label: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any],
    ) -> AuditEventRecord: ...
    def list(
        self, brand_id: str, limit: int = 20, offset: int = 0
    ) -> Page[AuditEventRecord]: ...


class CacheRepo(Protocol):
    """Protocol for source response caching with TTL awareness."""

    def get(self, key: str, max_age_s: int | None = None) -> CachedResponse | None: ...
    def put(
        self,
        key: str,
        source_id: str,
        request: dict[str, Any],
        response: dict[str, Any],
        ttl_seconds: int = 3600,
    ) -> None: ...
