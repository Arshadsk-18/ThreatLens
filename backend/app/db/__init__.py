"""Database module for ThreatLens v3."""

from .base import Base, UTCDateTime, generate_uuid, utc_now
from .models import (
    AnalystDecision,
    Assessment,
    AuditEvent,
    Brand,
    CandidateAsset,
    EvaluationRun,
    Evidence,
    OfficialAsset,
    ResponseCache,
    Scan,
)
from .session import (
    DATABASE_URL,
    DEFAULT_SQLITE_URL,
    SessionLocal,
    create_db_engine,
    engine,
    get_engine_options,
    get_session,
    init_db,
    mark_interrupted_scans,
)

__all__ = [
    "DATABASE_URL",
    "DEFAULT_SQLITE_URL",
    "AnalystDecision",
    "Assessment",
    "AuditEvent",
    "Base",
    "Brand",
    "CandidateAsset",
    "EvaluationRun",
    "Evidence",
    "OfficialAsset",
    "ResponseCache",
    "Scan",
    "SessionLocal",
    "UTCDateTime",
    "create_db_engine",
    "engine",
    "generate_uuid",
    "get_engine_options",
    "get_session",
    "init_db",
    "mark_interrupted_scans",
    "utc_now",
]
