"""Backward compatibility module for fixture adapters.

Owner: Person 3 (backend/app/services/sources/demo.py)
Re-exports DemoFixtureAdapter and RecordedFixtureAdapter from their respective modules.
"""

from __future__ import annotations

from .fixtures_demo import DemoFixtureAdapter
from .fixtures_recorded import RecordedFixtureAdapter

__all__ = ["DemoFixtureAdapter", "RecordedFixtureAdapter"]
