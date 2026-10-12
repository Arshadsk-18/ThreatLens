"""Pure assessment, comparison and scoring interface specification.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 7, 8, 12
Owner: Person 4 (Detection, IdentityGuard, evaluation)
Branch: feat/detection

NOTE: Pure functions, zero network, zero database.
Person 4 owns IdentityGuard, signal computation, gates G1-G5, and comparison generation.
Do not pretend this stub implements scoring logic.
"""

from app.schemas.candidate import NormalizedCandidate
from app.schemas.comparison import FieldComparison
from app.schemas.context import BrandCtx, OfficialAssetCtx
from app.schemas.scoring import AssessmentResult, ScoringConfig


def assess(
    candidate: NormalizedCandidate,
    brand: BrandCtx,
    official_assets: list[OfficialAssetCtx],
    config: ScoringConfig,
) -> AssessmentResult:
    """Evaluate a candidate asset against brand context and active official assets.

    Pure function: no network, no database, deterministic.
    Implementation owned by Person 4.
    """
    raise NotImplementedError("Person 4 owns assess() implementation.")


def icon_similarity(hash_a: str, hash_b: str) -> float:
    """Compute normalized similarity (0.0 to 1.0) between two perceptual hashes.

    Implementation owned by Person 4.
    """
    raise NotImplementedError("Person 4 owns icon_similarity() implementation.")


def compare(
    candidate: NormalizedCandidate,
    official: OfficialAssetCtx,
) -> list[FieldComparison]:
    """Generate field-by-field comparison between candidate and official asset.

    Implementation owned by Person 4.
    """
    raise NotImplementedError("Person 4 owns compare() implementation.")
