"""Repository interfaces, factories, and implementations for ThreatLens."""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session, sessionmaker

from .in_memory import (
    InMemoryAssessmentRepo,
    InMemoryAssetRepo,
    InMemoryAuditRepo,
    InMemoryBrandRepo,
    InMemoryCacheRepo,
    InMemoryCandidateRepo,
    InMemoryDecisionRepo,
    InMemoryScanRepo,
)
from .protocols import (
    AssessmentRepo,
    AssetRepo,
    AuditEventRecord,
    AuditRepo,
    BrandRepo,
    CachedResponse,
    CacheRepo,
    CandidateRepo,
    ClearedRecord,
    DecisionRepo,
    DomainValidationError,
    EntityNotFoundError,
    FindingRecord,
    Page,
    ScanRepo,
    compute_content_hash,
)
from .sqlalchemy_repo import (
    SqlAlchemyAssessmentRepo,
    SqlAlchemyAssetRepo,
    SqlAlchemyAuditRepo,
    SqlAlchemyBrandRepo,
    SqlAlchemyCacheRepo,
    SqlAlchemyCandidateRepo,
    SqlAlchemyDecisionRepo,
    SqlAlchemyScanRepo,
)


class RepositoryBundle(NamedTuple):
    """Container holding all repositories for dependency injection."""

    brand_repo: BrandRepo
    asset_repo: AssetRepo
    scan_repo: ScanRepo
    candidate_repo: CandidateRepo
    assessment_repo: AssessmentRepo
    decision_repo: DecisionRepo
    audit_repo: AuditRepo
    cache_repo: CacheRepo


def create_in_memory_repositories() -> RepositoryBundle:
    """Create in-memory repository instances sharing state."""
    audit_repo = InMemoryAuditRepo()
    brand_repo = InMemoryBrandRepo()
    asset_repo = InMemoryAssetRepo(audit_repo=audit_repo)
    scan_repo = InMemoryScanRepo()
    candidate_repo = InMemoryCandidateRepo()
    decision_repo = InMemoryDecisionRepo(
        candidate_repo=candidate_repo, audit_repo=audit_repo
    )
    assessment_repo = InMemoryAssessmentRepo(
        candidate_repo=candidate_repo, decision_repo=decision_repo
    )
    cache_repo = InMemoryCacheRepo()

    return RepositoryBundle(
        brand_repo=brand_repo,
        asset_repo=asset_repo,
        scan_repo=scan_repo,
        candidate_repo=candidate_repo,
        assessment_repo=assessment_repo,
        decision_repo=decision_repo,
        audit_repo=audit_repo,
        cache_repo=cache_repo,
    )


def create_sqlalchemy_repositories(
    session_factory: sessionmaker[Session],
) -> RepositoryBundle:
    """Create SQLAlchemy repository instances bound to a session factory."""
    audit_repo = SqlAlchemyAuditRepo(session_factory=session_factory)
    brand_repo = SqlAlchemyBrandRepo(session_factory=session_factory)
    asset_repo = SqlAlchemyAssetRepo(
        session_factory=session_factory, audit_repo=audit_repo
    )
    scan_repo = SqlAlchemyScanRepo(session_factory=session_factory)
    candidate_repo = SqlAlchemyCandidateRepo(session_factory=session_factory)
    decision_repo = SqlAlchemyDecisionRepo(session_factory=session_factory)
    assessment_repo = SqlAlchemyAssessmentRepo(session_factory=session_factory)
    cache_repo = SqlAlchemyCacheRepo(session_factory=session_factory)

    return RepositoryBundle(
        brand_repo=brand_repo,
        asset_repo=asset_repo,
        scan_repo=scan_repo,
        candidate_repo=candidate_repo,
        assessment_repo=assessment_repo,
        decision_repo=decision_repo,
        audit_repo=audit_repo,
        cache_repo=cache_repo,
    )


def get_repository_bundle(
    kind: str = "in_memory", session_factory: sessionmaker[Session] | None = None
) -> RepositoryBundle:
    """Factory helper allowing Person 2 to swap implementations with one call."""
    if kind == "in_memory":
        return create_in_memory_repositories()
    elif kind == "sqlalchemy":
        if session_factory is None:
            from app.db.session import SessionLocal

            session_factory = SessionLocal
        return create_sqlalchemy_repositories(session_factory=session_factory)
    raise ValueError(f"Unknown repository kind: {kind}")


__all__ = [
    "AssessmentRepo",
    "AssetRepo",
    "AuditEventRecord",
    "AuditRepo",
    "BrandRepo",
    "CacheRepo",
    "CachedResponse",
    "CandidateRepo",
    "ClearedRecord",
    "DecisionRepo",
    "DomainValidationError",
    "EntityNotFoundError",
    "FindingRecord",
    "InMemoryAssessmentRepo",
    "InMemoryAssetRepo",
    "InMemoryAuditRepo",
    "InMemoryBrandRepo",
    "InMemoryCacheRepo",
    "InMemoryCandidateRepo",
    "InMemoryDecisionRepo",
    "InMemoryScanRepo",
    "Page",
    "RepositoryBundle",
    "ScanRepo",
    "SqlAlchemyAssessmentRepo",
    "SqlAlchemyAssetRepo",
    "SqlAlchemyAuditRepo",
    "SqlAlchemyBrandRepo",
    "SqlAlchemyCacheRepo",
    "SqlAlchemyCandidateRepo",
    "SqlAlchemyDecisionRepo",
    "SqlAlchemyScanRepo",
    "compute_content_hash",
    "create_in_memory_repositories",
    "create_sqlalchemy_repositories",
    "get_repository_bundle",
]
