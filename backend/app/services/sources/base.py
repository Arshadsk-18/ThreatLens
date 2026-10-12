"""SourceAdapter Protocol definition.

Owner: Person 3 (backend/app/services/sources/base.py)
Reference: Contract Section 12 (Internal Python interfaces)
"""

from __future__ import annotations

from typing import Protocol

from app.schemas import (
    NormalizedCandidate,
    QueryPlan,
    SourceHealth,
    SourceResult,
)


class SourceAdapter(Protocol):
    """Internal contract protocol for all external and fixture-backed source adapters."""

    source_id: str

    async def health_check(self) -> SourceHealth: ...

    async def search(
        self,
        plan: QueryPlan,
        limit: int,
        *,
        force_refresh: bool,
        allow_stale_cache: bool,
    ) -> SourceResult: ...

    async def lookup(self, identifier: str) -> NormalizedCandidate | None: ...
