"""Candidate detection, fuzzy look-alike identification, and scoring module."""

from .normalization import (
    classify_lookalike,
    detect_homoglyphs,
    fuzzy_levenshtein_similarity,
)
from .scoring import evaluate_lookalike_candidate

__all__ = [
    "classify_lookalike",
    "detect_homoglyphs",
    "evaluate_lookalike_candidate",
    "fuzzy_levenshtein_similarity",
]
