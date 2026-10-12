"""Pytest configuration and contract schema provider for sources tests.

Owner: Person 3 (allowed lane: backend/app/services/sources/**)
If Person 2 has already landed `backend/app/schemas/`, this imports directly.
Otherwise, this dynamically registers the contract Section 10 & 12 models into
`sys.modules['app.schemas']` during tests so sources code can import ONLY from
`app.schemas` without creating any forbidden files in `backend/app/schemas/`.
"""

from __future__ import annotations

import sys
import types
from datetime import datetime
from enum import Enum
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field

# Ensure repo root and backend/ are on sys.path
REPO_ROOT = Path(__file__).resolve().parents[5]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure app has __path__ for namespace package resolution
if "app" not in sys.modules:
    app_pkg = types.ModuleType("app")
    app_pkg.__path__ = [str(BACKEND_DIR / "app")]
    sys.modules["app"] = app_pkg
else:
    app_pkg = sys.modules["app"]
    if not hasattr(app_pkg, "__path__"):
        app_pkg.__path__ = [str(BACKEND_DIR / "app")]

try:
    import app.schemas  # type: ignore # noqa: F401
except ImportError:
    schemas_pkg = types.ModuleType("app.schemas")
    app_pkg.schemas = schemas_pkg
    sys.modules["app.schemas"] = schemas_pkg

    # Enums (Contract Section 10)
    class SourceMode(str, Enum):
        LIVE = "LIVE"
        CACHED = "CACHED"
        SIMULATED = "SIMULATED"

    class SourceStatus(str, Enum):
        CONNECTED = "CONNECTED"
        PARTIAL = "PARTIAL"
        NOT_CONNECTED = "NOT_CONNECTED"
        RATE_LIMITED = "RATE_LIMITED"
        ERROR = "ERROR"

    class ProviderErrorCode(str, Enum):
        TIMEOUT = "TIMEOUT"
        RATE_LIMITED = "RATE_LIMITED"
        AUTH_REQUIRED = "AUTH_REQUIRED"
        PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
        NOT_CONFIGURED = "NOT_CONFIGURED"
        INVALID_RESPONSE = "INVALID_RESPONSE"
        BLOCKED_URL = "BLOCKED_URL"

    class AssetType(str, Enum):
        IOS_APP = "IOS_APP"
        ANDROID_APP = "ANDROID_APP"
        SOCIAL_ACCOUNT = "SOCIAL_ACCOUNT"

    # Shared Schemas (Contract Section 12)
    class NormalizedCandidate(BaseModel):
        source_id: str
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
        source_mode: SourceMode
        retrieved_at: datetime
        matched_queries: list[str] = Field(default_factory=list)

    class PlannedQuery(BaseModel):
        term: str
        kind: str  # BASE | SPACING | SEPARATOR | ADDED_WORD | DISTINCTIVE
        priority: int

    class QueryPlan(BaseModel):
        brand_id: UUID
        queries: list[PlannedQuery]

    class SourceResult(BaseModel):
        source_id: str
        status: SourceStatus
        source_mode: SourceMode | None
        retrieved_at: datetime | None
        candidates: list[NormalizedCandidate]
        queries_executed: int
        cache_hit_count: int
        error_code: ProviderErrorCode | None
        message: str
        duration_ms: int

    class SourceHealth(BaseModel):
        source_id: str
        display_name: str
        platform: str
        asset_types: list[AssetType]
        status: SourceStatus
        supported_modes: list[SourceMode]
        default_mode: SourceMode
        last_checked_at: datetime | None = None
        rate_limit_note: str | None = None
        message: str

    for obj in [
        SourceMode,
        SourceStatus,
        ProviderErrorCode,
        AssetType,
        NormalizedCandidate,
        PlannedQuery,
        QueryPlan,
        SourceResult,
        SourceHealth,
    ]:
        setattr(schemas_pkg, obj.__name__, obj)

    # Submodule app.schemas.candidate
    candidate_mod = types.ModuleType("app.schemas.candidate")
    candidate_mod.NormalizedCandidate = NormalizedCandidate
    candidate_mod.PlannedQuery = PlannedQuery
    candidate_mod.QueryPlan = QueryPlan
    candidate_mod.SourceResult = SourceResult
    sys.modules["app.schemas.candidate"] = candidate_mod

    # Submodule app.schemas.sources
    sources_mod = types.ModuleType("app.schemas.sources")
    sources_mod.SourceHealth = SourceHealth
    sys.modules["app.schemas.sources"] = sources_mod

    # Submodule app.schemas.enums
    enums_mod = types.ModuleType("app.schemas.enums")
    enums_mod.SourceMode = SourceMode
    enums_mod.SourceStatus = SourceStatus
    enums_mod.ProviderErrorCode = ProviderErrorCode
    enums_mod.AssetType = AssetType
    sys.modules["app.schemas.enums"] = enums_mod
