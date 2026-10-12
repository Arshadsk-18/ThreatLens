"""Deterministic text and name similarity utilities."""
from __future__ import annotations

from app.services.normalization.name_similarity import calculate_name_similarity


def compute_name_similarity(official_name: str, candidate_name: str) -> float:
    """Compute token and string name similarity score between official brand and candidate name."""
    return calculate_name_similarity(official_name, candidate_name).name_similarity
