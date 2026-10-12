"""Scoring service package.

Contract Section 12 re-exports.
"""

try:
    from app.services.scoring.models import AssessmentResult, NormalizedCandidate, ScoringConfig
except (ImportError, ModuleNotFoundError):
    from app.services.scoring.models import (
        AssessmentResult,
        NormalizedCandidate,
        ScoringConfig,
    )

__all__ = ["AssessmentResult", "NormalizedCandidate", "ScoringConfig"]
