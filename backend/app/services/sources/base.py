"""Source adapter interface specification.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 12
Owner: Person 3 (Discovery and Connectors)
Branch: feat/discovery

NOTE: This file defines the Protocol interface agreed between Person 2 and Person 3.
Person 3 owns the concrete implementation of live source adapters (Apple, Bluesky).
Do not replace this Protocol with a concrete implementation here.
"""

from typing import Protocol, runtime_checkable

from app.schemas.candidate import NormalizedCandidate, QueryPlan, SourceResult
from app.schemas.source import SourceHealth


@runtime_checkable
class SourceAdapter(Protocol):
    """Protocol for external platform connectors."""

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
