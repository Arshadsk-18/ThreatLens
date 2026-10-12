"""Prefill validation service wrapper."""
from __future__ import annotations

from app.services.sources.prefill import parse_prefill_input


def validate_prefill_url(url: str) -> None:
    """Validate prefill URL against domain allowlists, raising ValueError on violation."""
    parse_prefill_input(url, None, None)
