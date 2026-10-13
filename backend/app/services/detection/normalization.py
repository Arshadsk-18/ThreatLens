"""Candidate normalization & fuzzy look-alike detection engine.

Implements Levenshtein distance, normalized string similarity, homoglyph mapping
(including 0 for o, 1 for l, rn for m), character swaps, appended/prepended words,
and spacing/punctuation variations.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Any

from app.schemas.enums import LookalikeTechnique
from app.services.normalization.name_similarity import (
    HOMOGLYPH_MAP,
    normalize_name,
)
from app.services.normalization.techniques import (
    classify_technique,
)

# Extended substitutions: numbers to letters, multi-char lookalikes
EXTENDED_SUBSTITUTIONS: list[tuple[str, str]] = [
    ("0", "o"),
    ("1", "l"),
    ("3", "e"),
    ("4", "a"),
    ("5", "s"),
    ("8", "b"),
    ("@", "a"),
    ("$", "s"),
    ("rn", "m"),
    ("vv", "w"),
]

PUNCT_SPLIT_REGEX = re.compile(r"[-_.\s]+")


def detect_homoglyphs(text: str) -> tuple[str, bool, list[str]]:
    """Detect and replace digit/symbol/homoglyph substitutions (0->o, 1->l, rn->m, etc.)."""
    cleaned = text.lower()
    detected_replacements: list[str] = []
    has_homoglyph = False

    # Check multi-char and digit substitutions
    for target, replacement in EXTENDED_SUBSTITUTIONS:
        if target in cleaned:
            cleaned = cleaned.replace(target, replacement)
            has_homoglyph = True
            detected_replacements.append(f"{target}->{replacement}")

    # Check Unicode homoglyphs from HOMOGLYPH_MAP
    norm_text, unicode_homo = normalize_name(text)
    if unicode_homo:
        has_homoglyph = True
        detected_replacements.append("unicode_confusable")

    return cleaned, has_homoglyph, detected_replacements


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute exact Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def fuzzy_levenshtein_similarity(s1: str, s2: str) -> float:
    """Calculate normalized Levenshtein similarity between 0.0 and 1.0."""
    clean1 = "".join(c for c in s1.lower() if c.isalnum())
    clean2 = "".join(c for c in s2.lower() if c.isalnum())
    if not clean1 or not clean2:
        return 0.0
    dist = levenshtein_distance(clean1, clean2)
    max_len = max(len(clean1), len(clean2))
    return round(max(0.0, 1.0 - (dist / max_len)), 3)


def classify_lookalike(
    observed_name: str,
    brand_name: str,
    distinctive_tokens: list[str] | None = None,
) -> tuple[bool, LookalikeTechnique, float, str, dict[str, Any]]:
    """Comprehensive lookalike classifier catching:
    - Character swaps & homoglyphs (e.g. 0 for o, 1 for l, rn for m)
    - Appended / prepended words (e.g. {brand}-support, {brand}help, official-{brand})
    - Spacing and punctuation variations (e.g. {b-r-a-n-d}, {brand} app)
    - Fuzzy string similarity (Levenshtein distance & normalized string similarity)

    Returns:
        (lookalike_detected, technique, similarity, reason, metadata)
    """
    obs_clean = observed_name.strip()
    brand_clean = brand_name.strip()

    metadata: dict[str, Any] = {
        "observed": obs_clean,
        "brand": brand_clean,
        "lookalike_detected": False,
    }

    # 1. First run canonical technique classifier
    tech, meta_tech = classify_technique(observed=obs_clean, official=brand_clean)
    metadata.update(meta_tech)

    # 2. Check extended homoglyph / leetspeak substitutions (0 for o, 1 for l, rn for m)
    dehomo_obs, has_ext_homo, ext_replacements = detect_homoglyphs(obs_clean)
    dehomo_brand, _, _ = detect_homoglyphs(brand_clean)

    # 3. Normalized alphanumeric strings
    alnum_obs = "".join(c for c in obs_clean.lower() if c.isalnum())
    alnum_brand = "".join(c for c in brand_clean.lower() if c.isalnum())
    alnum_dehomo_obs = "".join(c for c in dehomo_obs if c.isalnum())
    alnum_dehomo_brand = "".join(c for c in dehomo_brand if c.isalnum())

    # Levenshtein & sequence similarity
    seq_sim = round(difflib.SequenceMatcher(None, brand_clean.lower(), obs_clean.lower()).ratio(), 3)
    lev_sim = fuzzy_levenshtein_similarity(obs_clean, brand_clean)
    effective_sim = max(seq_sim, lev_sim)
    metadata["levenshtein_similarity"] = lev_sim
    metadata["sequence_similarity"] = seq_sim

    # 4. Check Spacing / Punctuation variations ({b-r-a-n-d}, {brand} app)
    if alnum_obs == alnum_brand and obs_clean.lower() != brand_clean.lower():
        metadata["lookalike_detected"] = True
        chosen_tech = LookalikeTechnique.SEPARATOR if any(c in "-_./" for c in obs_clean) else LookalikeTechnique.SPACING
        return (
            True,
            chosen_tech,
            1.0,
            f"{chosen_tech.value.title()} variation with identical alphanumeric character sequence.",
            metadata,
        )

    # 5. Check Character Swap
    if tech == LookalikeTechnique.CHARACTER_SWAP:
        metadata["lookalike_detected"] = True
        return (
            True,
            LookalikeTechnique.CHARACTER_SWAP,
            max(0.85, effective_sim),
            "Character transposition swap detected in brand name.",
            metadata,
        )

    # 6. Check Appended / Prepended words ({brand}-support, {brand}help, official-{brand})
    # If canonical classifier already flagged ADDED_WORD, prioritize it
    obs_lower = obs_clean.lower()
    brand_lower = brand_clean.lower()
    tokens_obs = [t for t in PUNCT_SPLIT_REGEX.split(obs_lower) if t]
    tokens_brand = [t for t in PUNCT_SPLIT_REGEX.split(brand_lower) if t]

    has_all_brand_tokens = all(t in tokens_obs for t in tokens_brand)
    is_pre_or_appended = (
        alnum_obs.startswith(alnum_brand)
        or alnum_obs.endswith(alnum_brand)
        or brand_lower in obs_lower
        or has_all_brand_tokens
    )

    if (tech == LookalikeTechnique.ADDED_WORD or is_pre_or_appended) and len(alnum_obs) > len(alnum_brand):
        metadata["lookalike_detected"] = True
        return (
            True,
            LookalikeTechnique.ADDED_WORD,
            max(0.75, effective_sim),
            "Brand name present with appended or prepended terms/keywords.",
            metadata,
        )

    # 7. Check Homoglyphs / Substitutions (0 for o, 1 for l, rn for m)
    brand_is_homoglyphed = (tech == LookalikeTechnique.HOMOGLYPH) or (
        has_ext_homo and (
            (alnum_dehomo_obs == alnum_brand and alnum_obs != alnum_brand)
            or (alnum_brand not in alnum_obs and (alnum_brand in alnum_dehomo_obs or alnum_dehomo_brand in alnum_dehomo_obs))
        )
    )
    if brand_is_homoglyphed:
        metadata["lookalike_detected"] = True
        metadata["ext_replacements"] = ext_replacements
        return (
            True,
            LookalikeTechnique.HOMOGLYPH,
            max(0.85, effective_sim),
            f"Homoglyph / substitution detected ({', '.join(ext_replacements)}).",
            metadata,
        )

    # 8. Check token overlap using distinctive tokens (e.g. "kaveri")
    distinctive = [t.lower() for t in (distinctive_tokens or tokens_brand) if t]
    for dt in distinctive:
        if dt in obs_lower or dt in alnum_obs:
            metadata["lookalike_detected"] = True
            return (
                True,
                LookalikeTechnique.ADDED_WORD,
                max(0.70, effective_sim),
                f"Distinctive brand token '{dt}' matched in candidate name.",
                metadata,
            )

    # 9. Generic technique classification (omission, repetition, keyboard adjacent)
    if tech != LookalikeTechnique.NONE:
        metadata["lookalike_detected"] = True
        return (
            True,
            tech,
            effective_sim,
            f"Pattern matching technique {tech.value}.",
            metadata,
        )

    # 10. High fuzzy similarity threshold (>= 0.75)
    if effective_sim >= 0.75:
        metadata["lookalike_detected"] = True
        return (
            True,
            LookalikeTechnique.HOMOGLYPH if has_ext_homo else LookalikeTechnique.ADDED_WORD,
            effective_sim,
            f"Fuzzy Levenshtein similarity ({int(effective_sim * 100)}%) exceeds detection threshold.",
            metadata,
        )

    # 10. High fuzzy similarity threshold (>= 0.75)
    if effective_sim >= 0.75:
        metadata["lookalike_detected"] = True
        return (
            True,
            LookalikeTechnique.HOMOGLYPH if has_ext_homo else LookalikeTechnique.ADDED_WORD,
            effective_sim,
            f"Fuzzy Levenshtein similarity ({int(effective_sim * 100)}%) exceeds detection threshold.",
            metadata,
        )

    return (
        False,
        LookalikeTechnique.NONE,
        effective_sim,
        "No lookalike pattern detected.",
        metadata,
    )
