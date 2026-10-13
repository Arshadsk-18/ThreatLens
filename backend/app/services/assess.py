"""Pure assessment, comparison and scoring interface specification.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 7, 8, 12
Pure functions, zero network, zero database.
"""

from __future__ import annotations

from app.schemas.candidate import NormalizedCandidate
from app.schemas.comparison import FieldComparison
from app.schemas.context import BrandCtx, OfficialAssetCtx
from app.schemas.scoring import AssessmentResult, ScoringConfig
from app.services.assess.engine import assess
from app.services.compare.comparison import compare, icon_similarity

__all__ = [
    "AssessmentResult",
    "BrandCtx",
    "FieldComparison",
    "NormalizedCandidate",
    "OfficialAssetCtx",
    "ScoringConfig",
    "assess",
    "compare",
    "icon_similarity",
]
