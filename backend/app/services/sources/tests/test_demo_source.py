"""Unit tests for DEMO and Recorded fixture adapters.

Owner: Person 3 (backend/app/services/sources/tests/test_demo_source.py)
Reference: Contract Section 5.3, Appendix B
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.schemas import PlannedQuery, QueryPlan, SourceMode, SourceStatus
from app.services.sources.demo import DemoFixtureAdapter, RecordedFixtureAdapter


@pytest.fixture
def plan() -> QueryPlan:
    return QueryPlan(
        brand_id=uuid4(),
        queries=[
            PlannedQuery(term="kaveri bank", kind="BASE", priority=1),
        ],
    )


@pytest.mark.asyncio
async def test_demo_fixture_adapter_makes_zero_network_calls(plan: QueryPlan) -> None:
    adapter = DemoFixtureAdapter()
    result = await adapter.search(plan, limit=10)

    assert result.status == SourceStatus.CONNECTED
    assert result.source_id == "demo_fixtures"
    assert result.source_mode == SourceMode.SIMULATED
    assert len(result.candidates) > 0

    for cand in result.candidates:
        assert cand.source_mode == SourceMode.SIMULATED


@pytest.mark.asyncio
async def test_recorded_fixture_adapter_makes_zero_network_calls(
    plan: QueryPlan,
) -> None:
    adapter = RecordedFixtureAdapter()
    result = await adapter.search(plan, limit=10)

    assert result.status == SourceStatus.CONNECTED
    assert result.source_id == "recorded_fixtures"
    assert result.source_mode == SourceMode.CACHED
    assert len(result.candidates) > 0

    for cand in result.candidates:
        assert cand.source_mode == SourceMode.CACHED
