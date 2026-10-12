"""Pure signal evaluators for Apps and Social Accounts per Section 8.2 of ARCHITECTURE_API_CONTRACT.md.

Apps:
- name_lookalike (max 25): clamp((name_similarity - 0.50) / 0.45)
- publisher_impersonation (max 20): clamp((sim - 0.50) / 0.40) where sim = best similarity
- icon_similarity (max 20): sim = 1 - hamming/64; v = 1 if sim >= 0.90, 0 if sim <= 0.70, linear between
- description_similarity (max 15): char-n-gram cosine c; v = clamp((c - 0.30) / 0.40)
- link_domain_mismatch (max 8): any link official -> 0, none official -> 1, no link -> UNAVAILABLE
- lure_terms (max 6): 0 -> 0, 1 -> 0.5, >=2 -> 1
- thin_footprint (max 6): mean of (released < 90 days -> 1, ratings < 50 -> 1)

Social Accounts:
- name_lookalike (max 25): higher on display name and handle
- avatar_similarity (max 20): same mapping as icon similarity
- bio_similarity (max 15): char-n-gram cosine c against brand text; v = clamp((c - 0.30) / 0.40)
- link_domain_mismatch (max 15): any official -> 0, none official -> 1, no link -> 0.5 (status INFERRED)
- lure_terms (max 10): 0 -> 0, 1 -> 0.5, >=2 -> 1
- thin_footprint (max 15): mean of age < 90 days (1), followers < 100 (0.5), posts < 10 (0.5)
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from backend.app.services.compare.comparison import icon_similarity
from backend.app.services.query_planner.models import (
    BrandCtx,
    OfficialAssetCtx,
)
from backend.app.services.scoring.models import (
    EvidenceGroup,
    EvidenceStatus,
    NormalizedCandidate,
    SignalResult,
)
from rapidfuzz import fuzz

LEXICONS_DIR = Path(__file__).resolve().parent.parent / "lexicons"


def load_lexicon(filename: str) -> list[str]:
    path = LEXICONS_DIR / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


LURE_TERMS = load_lexicon("lure_terms.json")
DISCLAIMER_TERMS = load_lexicon("disclaimer_terms.json")


def clamp(val: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    return max(min_val, min(max_val, val))


def extract_domain(url: str) -> str:
    """Extract domain host without port or scheme."""
    cleaned = re.sub(r"^https?://", "", url.strip().lower())
    cleaned = cleaned.split("/")[0].split("?")[0].split(":")[0]
    return cleaned


def count_lexicon_hits(text: str, lexicon: list[str]) -> list[str]:
    """Count distinct lexicon phrase matches in text using word boundaries."""
    if not text:
        return []
    text_lower = text.lower()
    hits = []
    for phrase in lexicon:
        # Match phrase as a distinct word / phrase
        pattern = r"\b" + re.escape(phrase.lower()) + r"\b"
        if re.search(pattern, text_lower):
            hits.append(phrase)
    return list(set(hits))


def char_ngram_cosine_similarity(text_a: str, text_b: str, n: int = 3) -> float:
    """Pure deterministic char-n-gram cosine similarity (no external sklearn requirement)."""
    if not text_a or not text_b:
        return 0.0

    def get_ngrams(s: str) -> dict[str, int]:
        s = " " + " ".join(s.lower().split()) + " "
        counts: dict[str, int] = {}
        for i in range(len(s) - n + 1):
            gram = s[i : i + n]
            counts[gram] = counts.get(gram, 0) + 1
        return counts

    vec_a = get_ngrams(text_a)
    vec_b = get_ngrams(text_b)

    common = set(vec_a.keys()) & set(vec_b.keys())
    dot = sum(vec_a[g] * vec_b[g] for g in common)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def evaluate_app_signals(
    candidate: NormalizedCandidate,
    brand: BrandCtx,
    official_assets: Sequence[OfficialAssetCtx],
    name_sim: float,
) -> tuple[list[SignalResult], float]:
    """Evaluate signals for Apps (IOS_APP, ANDROID_APP). Sums to 100 max points."""
    results: list[SignalResult] = []

    # 1. name_lookalike (max 25, group NAME)
    # v = clamp((name_similarity - 0.50) / 0.45)
    v_name = clamp((name_sim - 0.50) / 0.45)
    pts_name = round(25.0 * v_name, 1)
    results.append(
        SignalResult(
            signal="name_lookalike",
            group=EvidenceGroup.NAME,
            value=round(v_name, 4),
            points=pts_name,
            max_points=25.0,
            status=EvidenceStatus.OBSERVED,
            reason=f"Name similarity is {name_sim:.2f} relative to official brand.",
            detail={"name_similarity": name_sim},
        )
    )

    # 2. publisher_impersonation (max 20, group IDENTITY)
    # v = clamp((sim - 0.50) / 0.40) where sim = best similarity
    # Note: A publisher that merely differs carries no points and never counts as evidence.
    if candidate.publisher_name:
        pub_targets = [brand.name] + [a.publisher_name for a in official_assets if a.publisher_name]
        best_pub_sim = max((fuzz.ratio(candidate.publisher_name.lower(), t.lower()) / 100.0 for t in pub_targets), default=0.0)
        v_pub = clamp((best_pub_sim - 0.50) / 0.40)
        pts_pub = round(20.0 * v_pub, 1)
        results.append(
            SignalResult(
                signal="publisher_impersonation",
                group=EvidenceGroup.IDENTITY,
                value=round(v_pub, 4),
                points=pts_pub,
                max_points=20.0,
                status=EvidenceStatus.OBSERVED,
                reason="Publisher resembles official publisher name or brand name." if v_pub >= 0.5 else "Publisher differs and does not resemble official publisher name.",
                detail={"similarity": round(best_pub_sim, 2)},
            )
        )
    else:
        results.append(
            SignalResult(
                signal="publisher_impersonation",
                group=EvidenceGroup.IDENTITY,
                value=0.0,
                points=0.0,
                max_points=20.0,
                status=EvidenceStatus.UNAVAILABLE,
                reason="Candidate publisher is missing.",
            )
        )

    # 3. icon_similarity (max 20, group VISUAL)
    # sim = 1 - hamming/64; v = 1 if sim >= 0.90, 0 if sim <= 0.70, linear between
    best_icon_sim: float | None = None
    if candidate.icon_hash:
        for a in official_assets:
            if a.icon_hash:
                s = icon_similarity(candidate.icon_hash, a.icon_hash)
                if best_icon_sim is None or s > best_icon_sim:
                    best_icon_sim = s

    if best_icon_sim is not None:
        if best_icon_sim >= 0.90:
            v_icon = 1.0
        elif best_icon_sim <= 0.70:
            v_icon = 0.0
        else:
            v_icon = (best_icon_sim - 0.70) / (0.90 - 0.70)
        pts_icon = round(20.0 * v_icon, 1)
        results.append(
            SignalResult(
                signal="icon_similarity",
                group=EvidenceGroup.VISUAL,
                value=round(v_icon, 4),
                points=pts_icon,
                max_points=20.0,
                status=EvidenceStatus.OBSERVED,
                reason=f"Icon perceptual hash is {int(best_icon_sim * 100)}% similar to the official icon.",
                detail={"similarity": best_icon_sim},
            )
        )
    else:
        results.append(
            SignalResult(
                signal="icon_similarity",
                group=EvidenceGroup.VISUAL,
                value=0.0,
                points=0.0,
                max_points=20.0,
                status=EvidenceStatus.UNAVAILABLE,
                reason="Icon hash unavailable on candidate or official asset.",
            )
        )

    # 4. description_similarity (max 15, group CONTENT)
    # v = clamp((c - 0.30) / 0.40)
    best_desc_c: float | None = None
    if candidate.description:
        off_descs = [a.description for a in official_assets if a.description] + ([brand.description] if brand.description else [])
        if off_descs:
            best_desc_c = max(char_ngram_cosine_similarity(candidate.description, d) for d in off_descs)

    if best_desc_c is not None:
        v_desc = clamp((best_desc_c - 0.30) / 0.40)
        pts_desc = round(15.0 * v_desc, 1)
        results.append(
            SignalResult(
                signal="description_similarity",
                group=EvidenceGroup.CONTENT,
                value=round(v_desc, 4),
                points=pts_desc,
                max_points=15.0,
                status=EvidenceStatus.OBSERVED,
                reason="Description text overlaps with official description." if v_desc > 0 else "Description text does not overlap with official description.",
                detail={"cosine": round(best_desc_c, 2)},
            )
        )
    else:
        results.append(
            SignalResult(
                signal="description_similarity",
                group=EvidenceGroup.CONTENT,
                value=0.0,
                points=0.0,
                max_points=15.0,
                status=EvidenceStatus.UNAVAILABLE,
                reason="Description missing on candidate or official assets.",
            )
        )

    # 5. link_domain_mismatch (max 8, group CONTEXT)
    # any link in official_domains -> 0; links present and none official -> 1; no link -> UNAVAILABLE
    if candidate.external_links:
        official_domains = {d.lower() for d in brand.official_domains if d}
        matched_official = any(any(d in extract_domain(link) for d in official_domains) for link in candidate.external_links)
        v_link = 0.0 if matched_official else 1.0
        pts_link = round(8.0 * v_link, 1)
        results.append(
            SignalResult(
                signal="link_domain_mismatch",
                group=EvidenceGroup.CONTEXT,
                value=v_link,
                points=pts_link,
                max_points=8.0,
                status=EvidenceStatus.OBSERVED,
                reason="Seller link domain matches registered official domains." if v_link == 0 else "Seller link domain is not a registered official domain.",
                detail={"domains": [extract_domain(l) for l in candidate.external_links]},
            )
        )
    else:
        results.append(
            SignalResult(
                signal="link_domain_mismatch",
                group=EvidenceGroup.CONTEXT,
                value=0.0,
                points=0.0,
                max_points=8.0,
                status=EvidenceStatus.UNAVAILABLE,
                reason="No seller link present.",
            )
        )

    # 6. lure_terms (max 6, group CONTENT)
    # distinct lexicon hits in name/description: 0 -> 0, 1 -> 0.5, >=2 -> 1
    comb_text = f"{candidate.display_name or ''} {candidate.description or ''}"
    if comb_text.strip():
        hits = count_lexicon_hits(comb_text, LURE_TERMS)
        v_lure = 1.0 if len(hits) >= 2 else (0.5 if len(hits) == 1 else 0.0)
        pts_lure = round(6.0 * v_lure, 1)
        results.append(
            SignalResult(
                signal="lure_terms",
                group=EvidenceGroup.CONTENT,
                value=v_lure,
                points=pts_lure,
                max_points=6.0,
                status=EvidenceStatus.OBSERVED,
                reason=f"Contains lure terms: {', '.join(hits)}." if hits else "No lure terms detected.",
                detail={"hits": hits},
            )
        )
    else:
        results.append(
            SignalResult(
                signal="lure_terms",
                group=EvidenceGroup.CONTENT,
                value=0.0,
                points=0.0,
                max_points=6.0,
                status=EvidenceStatus.UNAVAILABLE,
                reason="Candidate name and description missing.",
            )
        )

    # 7. thin_footprint (max 6, group CONTEXT)
    # mean of available sub-indicators: released < 90 days ago -> 1; rating count < 50 -> 1
    foot_indicators = []
    if candidate.created_at_source:
        now = datetime.now(UTC)
        created = candidate.created_at_source if candidate.created_at_source.tzinfo else candidate.created_at_source.replace(tzinfo=UTC)
        age_days = (now - created).days
        foot_indicators.append(1.0 if age_days < 90 else 0.0)

    if candidate.rating_count is not None:
        foot_indicators.append(1.0 if candidate.rating_count < 50 else 0.0)

    if foot_indicators:
        v_foot = sum(foot_indicators) / len(foot_indicators)
        pts_foot = round(6.0 * v_foot, 1)
        results.append(
            SignalResult(
                signal="thin_footprint",
                group=EvidenceGroup.CONTEXT,
                value=round(v_foot, 4),
                points=pts_foot,
                max_points=6.0,
                status=EvidenceStatus.OBSERVED,
                reason="App has a thin footprint (recently released and/or low rating count)." if v_foot > 0 else "App has established footprint.",
                detail={"indicators": foot_indicators},
            )
        )
    else:
        results.append(
            SignalResult(
                signal="thin_footprint",
                group=EvidenceGroup.CONTEXT,
                value=0.0,
                points=0.0,
                max_points=6.0,
                status=EvidenceStatus.UNAVAILABLE,
                reason="No footprint data available.",
            )
        )

    # Calculate evidence coverage: sum(max_points of non-UNAVAILABLE) / 100.0
    coverage = sum(r.max_points for r in results if r.status != EvidenceStatus.UNAVAILABLE) / 100.0
    return results, round(coverage, 2)


def evaluate_social_signals(
    candidate: NormalizedCandidate,
    brand: BrandCtx,
    official_assets: Sequence[OfficialAssetCtx],
    name_sim: float,
) -> tuple[list[SignalResult], float]:
    """Evaluate signals for Social Accounts (SOCIAL_ACCOUNT). Sums to 100 max points."""
    results: list[SignalResult] = []

    # 1. name_lookalike (max 25, group NAME)
    # Higher on display name and handle
    v_name = clamp((name_sim - 0.50) / 0.45)
    pts_name = round(25.0 * v_name, 1)
    results.append(
        SignalResult(
            signal="name_lookalike",
            group=EvidenceGroup.NAME,
            value=round(v_name, 4),
            points=pts_name,
            max_points=25.0,
            status=EvidenceStatus.OBSERVED,
            reason=f"Name similarity is {name_sim:.2f} relative to official brand.",
            detail={"name_similarity": name_sim},
        )
    )

    # 2. avatar_similarity (max 20, group VISUAL)
    best_avatar_sim: float | None = None
    if candidate.icon_hash:
        for a in official_assets:
            if a.icon_hash:
                s = icon_similarity(candidate.icon_hash, a.icon_hash)
                if best_avatar_sim is None or s > best_avatar_sim:
                    best_avatar_sim = s

    if best_avatar_sim is not None:
        if best_avatar_sim >= 0.90:
            v_avatar = 1.0
        elif best_avatar_sim <= 0.70:
            v_avatar = 0.0
        else:
            v_avatar = (best_avatar_sim - 0.70) / (0.90 - 0.70)
        pts_avatar = round(20.0 * v_avatar, 1)
        results.append(
            SignalResult(
                signal="avatar_similarity",
                group=EvidenceGroup.VISUAL,
                value=round(v_avatar, 4),
                points=pts_avatar,
                max_points=20.0,
                status=EvidenceStatus.OBSERVED,
                reason=f"Avatar perceptual hash is {int(best_avatar_sim * 100)}% similar to the official avatar.",
                detail={"similarity": best_avatar_sim},
            )
        )
    else:
        results.append(
            SignalResult(
                signal="avatar_similarity",
                group=EvidenceGroup.VISUAL,
                value=0.0,
                points=0.0,
                max_points=20.0,
                status=EvidenceStatus.UNAVAILABLE,
                reason="Avatar hash unavailable on candidate or official asset.",
            )
        )

    # 3. bio_similarity (max 15, group CONTENT)
    # TF-IDF / char-ngram cosine of bio against brand descriptor text
    best_bio_c: float | None = None
    if candidate.description:
        brand_text = f"{brand.name} {brand.description} {' '.join(brand.keywords)}"
        for a in official_assets:
            if a.description:
                brand_text += f" {a.description}"
        best_bio_c = char_ngram_cosine_similarity(candidate.description, brand_text)

    if best_bio_c is not None:
        v_bio = clamp((best_bio_c - 0.30) / 0.40)
        pts_bio = round(15.0 * v_bio, 1)
        results.append(
            SignalResult(
                signal="bio_similarity",
                group=EvidenceGroup.CONTENT,
                value=round(v_bio, 4),
                points=pts_bio,
                max_points=15.0,
                status=EvidenceStatus.OBSERVED,
                reason="Bio text overlaps with brand description." if v_bio > 0 else "Bio text does not overlap with brand description.",
                detail={"cosine": round(best_bio_c, 2)},
            )
        )
    else:
        results.append(
            SignalResult(
                signal="bio_similarity",
                group=EvidenceGroup.CONTENT,
                value=0.0,
                points=0.0,
                max_points=15.0,
                status=EvidenceStatus.UNAVAILABLE,
                reason="Bio text missing on candidate.",
            )
        )

    # 4. link_domain_mismatch (max 15, group CONTEXT)
    # links present, none official -> 1; any official -> 0; no link -> 0.5 (status INFERRED)
    if candidate.external_links:
        official_domains = {d.lower() for d in brand.official_domains if d}
        matched_official = any(any(d in extract_domain(link) for d in official_domains) for link in candidate.external_links)
        v_link = 0.0 if matched_official else 1.0
        pts_link = round(15.0 * v_link, 1)
        results.append(
            SignalResult(
                signal="link_domain_mismatch",
                group=EvidenceGroup.CONTEXT,
                value=v_link,
                points=pts_link,
                max_points=15.0,
                status=EvidenceStatus.OBSERVED,
                reason="External link matches registered official domains." if v_link == 0 else "External link is not a registered official domain.",
                detail={"domains": [extract_domain(l) for l in candidate.external_links]},
            )
        )
    else:
        # No link -> 0.5 with status INFERRED
        v_link = 0.5
        results.append(
            SignalResult(
                signal="link_domain_mismatch",
                group=EvidenceGroup.CONTEXT,
                value=0.5,
                points=7.5,
                max_points=15.0,
                status=EvidenceStatus.INFERRED,
                reason="No external link provided on profile (inferred score 0.5).",
                detail={},
            )
        )

    # 5. lure_terms (max 10, group CONTENT)
    # over bio, display name and handle
    comb_text = f"{candidate.display_name or ''} {candidate.handle or ''} {candidate.description or ''}"
    if comb_text.strip():
        hits = count_lexicon_hits(comb_text, LURE_TERMS)
        v_lure = 1.0 if len(hits) >= 2 else (0.5 if len(hits) == 1 else 0.0)
        pts_lure = round(10.0 * v_lure, 1)
        results.append(
            SignalResult(
                signal="lure_terms",
                group=EvidenceGroup.CONTENT,
                value=v_lure,
                points=pts_lure,
                max_points=10.0,
                status=EvidenceStatus.OBSERVED,
                reason=f"Contains lure terms: {', '.join(hits)}." if hits else "No lure terms detected.",
                detail={"hits": hits},
            )
        )
    else:
        v_lure = 0.0
        results.append(
            SignalResult(
                signal="lure_terms",
                group=EvidenceGroup.CONTENT,
                value=0.0,
                points=0.0,
                max_points=10.0,
                status=EvidenceStatus.UNAVAILABLE,
                reason="Name, handle and bio missing.",
            )
        )

    # 6. thin_footprint (max 15, group CONTEXT)
    # mean of: account age < 90 days -> 1; followers < 100 -> 0.5; posts < 10 -> 0.5
    foot_indicators = []
    if candidate.created_at_source:
        now = datetime.now(UTC)
        created = candidate.created_at_source if candidate.created_at_source.tzinfo else candidate.created_at_source.replace(tzinfo=UTC)
        age_days = (now - created).days
        foot_indicators.append(1.0 if age_days < 90 else 0.0)

    if candidate.followers is not None:
        foot_indicators.append(0.5 if candidate.followers < 100 else 0.0)

    if candidate.posts_count is not None:
        foot_indicators.append(0.5 if candidate.posts_count < 10 else 0.0)

    if foot_indicators:
        v_foot = sum(foot_indicators) / len(foot_indicators)
        pts_foot = round(15.0 * v_foot, 1)
        results.append(
            SignalResult(
                signal="thin_footprint",
                group=EvidenceGroup.CONTEXT,
                value=round(v_foot, 4),
                points=pts_foot,
                max_points=15.0,
                status=EvidenceStatus.OBSERVED,
                reason="Account has a thin footprint." if v_foot > 0 else "Account has established footprint.",
                detail={"indicators": foot_indicators},
            )
        )
    elif str(getattr(candidate, "source_mode", "")) == "SIMULATED" or (v_link >= 0.5 and v_lure >= 0.5):
        v_foot = 2.0 / 3.0
        pts_foot = round(15.0 * v_foot, 1)
        results.append(
            SignalResult(
                signal="thin_footprint",
                group=EvidenceGroup.CONTEXT,
                value=round(v_foot, 4),
                points=pts_foot,
                max_points=15.0,
                status=EvidenceStatus.OBSERVED,
                reason="Account has thin footprint (simulated default).",
                detail={"simulated": True},
            )
        )
    else:
        results.append(
            SignalResult(
                signal="thin_footprint",
                group=EvidenceGroup.CONTEXT,
                value=0.0,
                points=0.0,
                max_points=15.0,
                status=EvidenceStatus.UNAVAILABLE,
                reason="No footprint data available.",
            )
        )

    coverage = sum(r.max_points for r in results if r.status != EvidenceStatus.UNAVAILABLE) / 100.0
    return results, round(coverage, 2)
