"""Cache repository and canonical key generator for external sources.

Owner: Person 3 (backend/app/services/sources/cache.py)
Reference: Contract Sections 5.5, 12, Phase 4 specs

Implements the Section 12 CacheRepo protocol until Person 5's database repository lands.
Raw payloads exist ONLY inside put(). Nothing else stores or logs them.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class CachedResponse:
    """Cached response envelope adhering to Contract Section 12."""

    key: str
    source_id: str
    request: dict[str, Any]
    response: dict[str, Any]
    retrieved_at: datetime

    @property
    def created_at(self) -> datetime:
        """Alias for retrieved_at."""
        return self.retrieved_at


class CacheRepo(Protocol):
    """Contract Section 12 CacheRepo Protocol."""

    def get(self, key: str, max_age_s: int | None = None) -> CachedResponse | None: ...
    def put(
        self,
        key: str,
        source_id: str,
        request: dict[str, Any],
        response: dict[str, Any],
    ) -> None: ...


def make_cache_key(source_id: str, operation: str, params: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 cache key from canonical JSON of {source_id, operation, params}.

    Rules:
    - Same request always gives the exact same key.
    - Different country, limit, term, or batch of DIDs gives a different key.
    - Uses sorted keys and compact separators for canonical JSON formatting.
    """
    canonical_dict = {
        "operation": operation,
        "params": params,
        "source_id": source_id,
    }
    canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class InMemoryCacheFake:
    """In-memory CacheRepo implementation fulfilling Contract Section 12.

    Swappable with zero adapter code change when Person 5 lands PostgreSQL cache.
    """

    def __init__(self, default_ttl_s: int | None = None) -> None:
        if default_ttl_s is not None:
            self._default_ttl_s = default_ttl_s
        else:
            try:
                self._default_ttl_s = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))
            except ValueError:
                self._default_ttl_s = 3600
        self._store: dict[str, CachedResponse] = {}

    def get(self, key: str, max_age_s: int | None = None) -> CachedResponse | None:
        """Retrieve cached entry.

        If max_age_s is specified, enforces age <= max_age_s.
        If max_age_s is None, returns the cached entry of any age (for stale fallback).
        """
        record = self._store.get(key)
        if record is None:
            return None
        if max_age_s is not None:
            if max_age_s <= 0:
                return None
            age = (datetime.now(UTC) - record.retrieved_at).total_seconds()
            if age < 0 or age > max_age_s:
                return None
        return record

    def get_stale(self, key: str) -> CachedResponse | None:
        """Retrieve cached entry regardless of TTL (convenience alias for get(key, None))."""
        return self.get(key, max_age_s=None)

    def put(
        self,
        key: str,
        source_id: str,
        request: dict[str, Any],
        response: dict[str, Any],
        *,
        retrieved_at: datetime | None = None,
    ) -> None:
        """Store raw response payload with retrieval timestamp."""
        record = CachedResponse(
            key=key,
            source_id=source_id,
            request=request,
            response=response,
            retrieved_at=retrieved_at or datetime.now(UTC),
        )
        self._store[key] = record

    def clear(self) -> None:
        """Clear all entries from in-memory store."""
        self._store.clear()


# Backward compatibility alias
InMemoryCacheRepo = InMemoryCacheFake

__all__ = [
    "CacheRepo",
    "CachedResponse",
    "InMemoryCacheFake",
    "InMemoryCacheRepo",
    "make_cache_key",
]
