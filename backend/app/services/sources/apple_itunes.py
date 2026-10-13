"""Apple iTunes source adapter module (alias for apple.py).

Provides Apple iTunes software search and lookup per Section 5.5, 11.3, 13.1.
"""

from __future__ import annotations

from .apple import (
    APPLE_URL_PATTERN,
    BUNDLE_ID_PATTERN,
    AppleItunesAdapter,
    map_apple_item,
    parse_apple_date,
)

__all__ = [
    "APPLE_URL_PATTERN",
    "BUNDLE_ID_PATTERN",
    "AppleItunesAdapter",
    "map_apple_item",
    "parse_apple_date",
]
