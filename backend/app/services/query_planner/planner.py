"""Query Planner service for ThreatLens v3.

Reference:
- Section 5.4 Query planner
- Section 12 Internal Python interfaces

Signature:
def plan_queries(brand: BrandCtx, assets: list[OfficialAssetCtx], source_id: str, max_queries: int) -> QueryPlan

Hard query bounds: max 8 for apple_itunes, max 6 for bluesky_public, hard cap 12.
Priority sequence:
1. BASE: brand name, normalized asset display names.
2. SPACING: spacing variants ("kaveribank" <-> "kaveri bank").
3. SEPARATOR: hyphen/dot variants ("kaveri-bank", "kaveri.bank").
4. ADDED_WORD: target brand + terms from list ("official", "support", "rewards", "kyc", "care", "app", "mobile", "loan").
5. DISTINCTIVE: distinctive tokens alone ("kaveri").

Deduplicate queries after normalization while preserving priority.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.services.normalization.name_similarity import normalize_name
from app.services.query_planner.models import (
    BrandCtx,
    OfficialAssetCtx,
    PlannedQuery,
    QueryPlan,
)

# Standard added terms per Section 5.4
ADDED_TERMS: list[str] = [
    "official",
    "support",
    "rewards",
    "kyc",
    "care",
    "app",
    "mobile",
    "loan",
]

# Source-specific default query limits per Section 5.4
SOURCE_DEFAULT_LIMITS: dict[str, int] = {
    "apple_itunes": 8,
    "bluesky_public": 6,
}
HARD_MAX_QUERIES = 12


def plan_queries(
    brand: BrandCtx,
    assets: Sequence[OfficialAssetCtx],
    source_id: str,
    max_queries: int | None = None,
) -> QueryPlan:
    """Generate ordered and bounded retrieval queries for a brand and source.

    Hard query bounds:
    - Default 8 for apple_itunes
    - Default 6 for bluesky_public
    - Hard maximum cap of 12 queries.
    """
    if brand is None:
        raise NotImplementedError("Person 4 plan_queries stub.")

    # 1. Determine effective query cap
    default_limit = SOURCE_DEFAULT_LIMITS.get(source_id, 8)
    if max_queries is None or max_queries <= 0:
        effective_cap = default_limit
    else:
        effective_cap = min(max_queries, default_limit, HARD_MAX_QUERIES)

    candidates: list[tuple[str, str]] = []  # list of (raw_term, kind)

    # 1. BASE: brand name, normalized asset display names
    candidates.append((brand.name, "BASE"))
    for asset in assets:
        if asset.is_active and asset.display_name:
            candidates.append((asset.display_name, "BASE"))

    # 2. SPACING: spacing variants ("kaveribank" <-> "kaveri bank")
    norm_brand, _ = normalize_name(brand.name)
    if " " in norm_brand:
        candidates.append((norm_brand.replace(" ", ""), "SPACING"))
    else:
        # If brand name was concatenated, e.g. "KaveriBank", generate spaced version if distinct tokens
        if brand.distinctive_tokens:
            for dt in brand.distinctive_tokens:
                if norm_brand.startswith(dt.lower()) and len(norm_brand) > len(dt):
                    spaced = dt.lower() + " " + norm_brand[len(dt):]
                    candidates.append((spaced, "SPACING"))

    for kw in brand.keywords:
        if kw:
            norm_kw, _ = normalize_name(kw)
            if " " in norm_kw:
                candidates.append((norm_kw.replace(" ", ""), "SPACING"))
            elif norm_kw != norm_brand.replace(" ", ""):
                candidates.append((norm_kw, "SPACING"))

    # 3. SEPARATOR: hyphen/dot variants ("kaveri-bank", "kaveri.bank")
    norm_brand, _ = normalize_name(brand.name)
    tokens = norm_brand.split()
    if len(tokens) > 1:
        candidates.append(("-".join(tokens), "SEPARATOR"))
        candidates.append((".".join(tokens), "SEPARATOR"))

    # 4. ADDED_WORD: target brand + terms from list
    # e.g., "kaveri bank official", "kaveri bank support", ...
    for term in ADDED_TERMS:
        candidates.append((f"{norm_brand} {term}", "ADDED_WORD"))

    # 5. DISTINCTIVE: distinctive tokens alone ("kaveri")
    if brand.distinctive_tokens:
        for dt in brand.distinctive_tokens:
            if dt:
                candidates.append((dt, "DISTINCTIVE"))
    elif tokens:
        # If no explicit distinctive tokens, first token or distinctive token
        candidates.append((tokens[0], "DISTINCTIVE"))

    # Deduplicate after normalization while preserving order/priority
    seen_normalized: set[str] = set()
    planned_queries: list[PlannedQuery] = []
    priority = 1

    for raw_term, kind in candidates:
        norm, _ = normalize_name(raw_term)
        if not norm or norm in seen_normalized:
            continue
        seen_normalized.add(norm)
        planned_queries.append(
            PlannedQuery(
                term=norm,
                kind=kind,
                priority=priority,
            )
        )
        priority += 1
        if len(planned_queries) >= effective_cap:
            break

    return QueryPlan(
        brand_id=brand.id,
        queries=planned_queries,
    )
