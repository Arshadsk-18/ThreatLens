"""Comparison service package.

Contract Section 12 re-exports.
"""

try:
    from app.services.compare.comparison import (
        FieldComparison,
        compare,
        hamming_distance_phash,
        hex_to_bin_str,
        icon_similarity,
    )
except (ImportError, ModuleNotFoundError):
    from backend.app.services.compare.comparison import (
        FieldComparison,
        compare,
        hamming_distance_phash,
        hex_to_bin_str,
        icon_similarity,
    )

__all__ = [
    "FieldComparison",
    "compare",
    "hamming_distance_phash",
    "hex_to_bin_str",
    "icon_similarity",
]
