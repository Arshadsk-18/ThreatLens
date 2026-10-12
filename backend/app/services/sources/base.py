"""SourceAdapter Protocol definition.

Owner: Person 3 (backend/app/services/sources/base.py)
Reference: Contract Section 12 (Internal Python interfaces)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas import (
    NormalizedCandidate,
    QueryPlan,
    SourceHealth,
    SourceResult,
)


@runtime_checkable
class SourceAdapter(Protocol):
    """Internal contract protocol for all external and fixture-backed source adapters."""

    source_id: str

    async def health_check(self) -> SourceHealth:
        """Check source connectivity and return current health status."""
        ...

    async def search(
        self,
        plan: QueryPlan,
        limit: int,
        *,
        force_refresh: bool,
        allow_stale_cache: bool,
    ) -> SourceResult:
        """Execute planned search queries against the provider."""
        ...

    async def lookup(self, identifier: str) -> NormalizedCandidate | None:
        """Lookup an exact asset by stable identifier or URL (used by prefill)."""
        ...
