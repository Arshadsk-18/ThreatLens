"""Query planner interface specification.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 5.4, 12
Owner: Person 4 (Detection, IdentityGuard, evaluation)
Branch: feat/detection

NOTE: This file defines the signature agreed between Person 2 and Person 4.
Person 4 owns brand term generation (base, spacing, separator, added-word, distinctive).
Do not pretend this stub implements term planning.
"""

from app.schemas.candidate import QueryPlan
from app.schemas.context import BrandCtx, OfficialAssetCtx


def plan_queries(
    brand: BrandCtx,
    assets: list[OfficialAssetCtx],
    source_id: str,
    max_queries: int,
) -> QueryPlan:
    """Generate bounded, ordered list of search queries for a provider source.

    Implementation owned by Person 4.
    """
    raise NotImplementedError("Person 4 owns query planner logic.")
