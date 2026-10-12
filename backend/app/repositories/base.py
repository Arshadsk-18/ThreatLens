"""Repository Protocol specifications.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 9, 12
Owner: Person 5 (Database, QA and reporting)
Branch: feat/database-qa

NOTE: This file defines the repository Protocols agreed between Person 2 and Person 5.
Person 5 owns the database models, migrations, and repository implementations (SQLite / Postgres).
Do not create a second permanent repository layer.
"""

from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from app.schemas.candidate import NormalizedCandidate
from app.schemas.common import PaginatedResponse
from app.schemas.context import BrandCtx, OfficialAssetCtx
from app.schemas.enums import ScanMode, ScanStage, ScanStatus
from app.schemas.scoring import AssessmentResult


@runtime_checkable
class BrandRepo(Protocol):
    """Protocol for brand storage and retrieval."""

    async def get_by_id(self, brand_id: UUID) -> BrandCtx | None: ...
    async def list_brands(
        self, limit: int = 20, offset: int = 0
    ) -> PaginatedResponse[BrandCtx]: ...


@runtime_checkable
class AssetRepo(Protocol):
    """Protocol for official asset storage and retrieval."""

    async def get_by_id(self, asset_id: UUID) -> OfficialAssetCtx | None: ...
    async def list_by_brand(
        self,
        brand_id: UUID,
        asset_type: str | None = None,
        relationship: str | None = None,
        is_verified: bool | None = None,
        is_active: bool | None = None,
    ) -> list[OfficialAssetCtx]: ...


@runtime_checkable
class ScanRepo(Protocol):
    """Protocol for scan run state management and lifecycle."""

    async def create(
        self,
        brand_id: UUID,
        mode: ScanMode,
        options: dict[str, Any],
    ) -> UUID: ...

    async def get_by_id(self, scan_id: UUID) -> Any | None: ...

    async def update_progress(
        self,
        scan_id: UUID,
        stage: ScanStage,
        progress_percent: int,
    ) -> None: ...

    async def append_event(
        self,
        scan_id: UUID,
        stage: ScanStage,
        level: str,
        message: str,
        source_id: str | None = None,
    ) -> None: ...

    async def finish(
        self,
        scan_id: UUID,
        status: ScanStatus,
        source_outcomes: list[dict[str, Any]],
        funnel: dict[str, int],
        findings_by_severity: dict[str, int],
        error_message: str | None = None,
    ) -> None: ...


@runtime_checkable
class CandidateRepo(Protocol):
    """Protocol for external candidate asset observation and decision memory."""

    async def upsert(
        self,
        candidate: NormalizedCandidate,
        brand_id: UUID,
        scan_id: UUID,
    ) -> Any: ...


@runtime_checkable
class AssessmentRepo(Protocol):
    """Protocol for persisting assessment results and querying findings / cleared items."""

    async def save(
        self,
        scan_id: UUID,
        candidate_asset_id: UUID,
        brand_id: UUID,
        result: AssessmentResult,
        evidence: list[dict[str, Any]],
    ) -> UUID: ...

    async def list_findings(
        self, filters: dict[str, Any]
    ) -> PaginatedResponse[Any]: ...
    async def list_cleared(self, filters: dict[str, Any]) -> PaginatedResponse[Any]: ...


@runtime_checkable
class DecisionRepo(Protocol):
    """Protocol for analyst decision history and audit events."""

    async def record_decision(
        self,
        candidate_asset_id: UUID,
        assessment_id: UUID | None,
        previous_status: str,
        new_status: str,
        decision_reason: str,
        notes: str | None,
        actor_label: str = "analyst",
    ) -> Any: ...


@runtime_checkable
class CacheRepo(Protocol):
    """Protocol for provider HTTP response caching."""

    async def get(
        self, key: str, max_age_s: int | None = None
    ) -> dict[str, Any] | None: ...
    async def put(
        self,
        key: str,
        source_id: str,
        request: dict[str, Any],
        response: dict[str, Any],
        ttl_seconds: int = 3600,
    ) -> None: ...
