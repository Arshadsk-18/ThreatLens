"""Common schema primitives for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 10
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard list response wrapper."""

    items: list[T] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0
