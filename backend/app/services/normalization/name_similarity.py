"""Name similarity and normalization for ThreatLens v3.

Reference:
- Section 8.1 Name normalization
- Section 8.6 Worked examples
- Section 8.7 Scoring walkthroughs
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from rapidfuzz import fuzz

# Common confusable / homoglyph mapping to Latin ASCII
# Cyrillic, Greek, fullwidth, and related lookalikes
HOMOGLYPH_MAP: dict[str, str] = {
    # Cyrillic small & capital
    "\u0430": "a",  # Cyrillic small letter a
    "\u0410": "A",  # Cyrillic capital letter A
    "\u0441": "c",  # Cyrillic small letter es
    "\u0421": "C",  # Cyrillic capital letter Es
    "\u0435": "e",  # Cyrillic small letter ie
    "\u0415": "E",  # Cyrillic capital letter Ie
    "\u0456": "i",  # Cyrillic small letter Byelorussian-Ukrainian i (U+0456)
    "\u0406": "I",  # Cyrillic capital letter Byelorussian-Ukrainian I
    "\u0458": "j",  # Cyrillic small letter je
    "\u0408": "J",  # Cyrillic capital letter Je
    "\u043e": "o",  # Cyrillic small letter o
    "\u041e": "O",  # Cyrillic capital letter O
    "\u0440": "p",  # Cyrillic small letter er
    "\u0420": "P",  # Cyrillic capital letter Er
    "\u0455": "s",  # Cyrillic small letter dze
    "\u0405": "S",  # Cyrillic capital letter Dze
    "\u0445": "x",  # Cyrillic small letter ha
    "\u0425": "X",  # Cyrillic capital letter Ha
    "\u0443": "y",  # Cyrillic small letter u
    "\u0423": "Y",  # Cyrillic capital letter U
    "\u0432": "v",  # Cyrillic small letter ve
    "\u0412": "B",  # Cyrillic capital letter Ve
    "\u0442": "t",  # Cyrillic small letter te
    "\u0422": "T",  # Cyrillic capital letter Te
    "\u043c": "m",  # Cyrillic small letter em
    "\u041c": "M",  # Cyrillic capital letter Em
    "\u043d": "h",  # Cyrillic small letter en
    "\u041d": "H",  # Cyrillic capital letter En
    # Greek
    "\u03b1": "a",  # Greek small letter alpha
    "\u0391": "A",  # Greek capital letter Alpha
    "\u03b2": "b",  # Greek small letter beta
    "\u0392": "B",  # Greek capital letter Beta
    "\u03bf": "o",  # Greek small letter omicron
    "\u039f": "O",  # Greek capital letter Omicron
    "\u03c1": "p",  # Greek small letter rho
    "\u03a1": "P",  # Greek capital letter Rho
    # Common mathematical / decorative monospace / Latin-like
    "\u2010": "-",  # hyphen
    "\u2011": "-",  # non-breaking hyphen
    "\u2012": "-",  # figure dash
    "\u2013": "-",  # en dash
    "\u2014": "-",  # em dash
}

# Generic tokens from section 8.1
DEFAULT_GENERIC_TOKENS: set[str] = {
    "bank",
    "banking",
    "official",
    "app",
    "mobile",
    "online",
    "support",
    "care",
    "help",
    "rewards",
    "secure",
    "pay",
    "money",
    "finance",
    "india",
    "ltd",
    "limited",
}

# Separators mapped to space (-_.)
SEPARATOR_REGEX = re.compile(r"[-_.\/]+")


@dataclass(frozen=True)
class NameSimilarityResult:
    name_similarity: float
    ratio_full: float
    token_score: float
    homoglyph_detected: bool
    normalized_candidate: str
    normalized_brand: str


def normalize_name(text: str) -> tuple[str, bool]:
    """Normalize a name per Section 8.1:
    - Unicode NFKC normalization
    - Homoglyph detection and mapping to Latin equivalents (flags if homoglyphs mapped)
    - Case-folding
    - Punctuation/separator mapping (-_./) to single space
    - Whitespace collapsing and trimming

    Returns:
        tuple[str, bool]: (normalized_string, homoglyph_detected)
    """
    if not text:
        return "", False

    # 1. NFKC normalization
    nfkc_text = unicodedata.normalize("NFKC", text)

    # 2. Map known confusables to Latin equivalents & track if homoglyph was mapped
    has_homoglyph = False
    mapped_chars = []
    for ch in nfkc_text:
        if ch in HOMOGLYPH_MAP:
            mapped_chars.append(HOMOGLYPH_MAP[ch])
            has_homoglyph = True
        else:
            mapped_chars.append(ch)
    text_after_homoglyphs = "".join(mapped_chars)

    # 3. Case-fold
    folded = text_after_homoglyphs.lower()

    # 4. Map separators to single space
    with_spaces = SEPARATOR_REGEX.sub(" ", folded)

    # 5. Collapse whitespace and trim
    collapsed = " ".join(with_spaces.split())

    return collapsed, has_homoglyph


def compute_token_score(
    brand_tokens: Sequence[str],
    candidate_tokens: Sequence[str],
    distinctive_tokens: Sequence[str] | None = None,
    generic_tokens_extra: Sequence[str] | None = None,
) -> float:
    """Calculate token_score according to section 8.1 reference formula:
    - Distinctive tokens: weight 1.0 (default: not in generic list, or explicitly in distinctive_tokens)
    - Generic tokens: weight 0.2 (generic list + generic_tokens_extra)
    - For each brand token t, m_t is max RapidFuzz token-to-token ratio >= 0.80, else 0.
    - Each unmatched candidate token is an extra token and weighs 0.2.
    - token_score = Σ(w_t * m_t) / (Σ w_t + 0.2 * extra_token_count)
    """
    if not brand_tokens:
        return 0.0

    all_generics = set(DEFAULT_GENERIC_TOKENS)
    if generic_tokens_extra:
        all_generics.update(t.lower() for t in generic_tokens_extra)

    explicit_distinctive = {t.lower() for t in distinctive_tokens} if distinctive_tokens else None

    weights: list[float] = []
    for bt in brand_tokens:
        bt_low = bt.lower()
        if explicit_distinctive is not None:
            w = 1.0 if bt_low in explicit_distinctive else 0.2
        else:
            w = 0.2 if bt_low in all_generics else 1.0
        weights.append(w)

    cand_matched = [False] * len(candidate_tokens)
    brand_matches: list[float] = []

    for bt in brand_tokens:
        best_ratio = 0.0
        best_cand_idx = -1
        for j, ct in enumerate(candidate_tokens):
            r = fuzz.ratio(bt, ct) / 100.0
            if r >= 0.80 and r > best_ratio:
                best_ratio = r
                best_cand_idx = j

        if best_ratio >= 0.80 and best_cand_idx >= 0:
            brand_matches.append(best_ratio)
            cand_matched[best_cand_idx] = True
        else:
            brand_matches.append(0.0)

    extra_token_count = sum(1 for matched in cand_matched if not matched)
    numerator = sum(w * m for w, m in zip(weights, brand_matches))
    denominator = sum(weights) + 0.2 * extra_token_count

    if denominator <= 0:
        return 0.0

    return numerator / denominator


def calculate_name_similarity(
    official_name: str,
    candidate_name: str,
    distinctive_tokens: Sequence[str] | None = None,
    generic_tokens_extra: Sequence[str] | None = None,
) -> NameSimilarityResult:
    """Implement reference name similarity formula from Section 8.1:
    1. ratio_full: max of RapidFuzz ratio on normalized strings and on space-collapsed strings (0-1).
    2. token_score: weighted token similarity with distinctive (1.0) and generic (0.2) weights.
    3. name_similarity: max(ratio_full, token_score) rounded to 2 decimal places.
    """
    norm_off, _off_homo = normalize_name(official_name)
    norm_cand, cand_homo = normalize_name(candidate_name)

    if not norm_off or not norm_cand:
        return NameSimilarityResult(
            name_similarity=0.0,
            ratio_full=0.0,
            token_score=0.0,
            homoglyph_detected=cand_homo,
            normalized_candidate=norm_cand,
            normalized_brand=norm_off,
        )

    # 1. ratio_full: max of RapidFuzz ratio on normalized string and on space-collapsed string
    ratio_norm = fuzz.ratio(norm_off, norm_cand) / 100.0
    off_collapsed = norm_off.replace(" ", "")
    cand_collapsed = norm_cand.replace(" ", "")
    ratio_nospace = fuzz.ratio(off_collapsed, cand_collapsed) / 100.0
    ratio_full = max(ratio_norm, ratio_nospace)

    # 2. token_score
    off_tokens = [t for t in norm_off.split() if t]
    cand_tokens = [t for t in norm_cand.split() if t]
    tok_score = compute_token_score(
        brand_tokens=off_tokens,
        candidate_tokens=cand_tokens,
        distinctive_tokens=distinctive_tokens,
        generic_tokens_extra=generic_tokens_extra,
    )

    # 3. name_similarity = max(ratio_full, token_score) rounded to 2 decimal places
    name_similarity = round(max(ratio_full, tok_score), 2)

    return NameSimilarityResult(
        name_similarity=name_similarity,
        ratio_full=round(ratio_full, 4),
        token_score=round(tok_score, 4),
        homoglyph_detected=cand_homo,
        normalized_candidate=norm_cand,
        normalized_brand=norm_off,
    )


def calculate_social_name_similarity(
    official_name: str,
    display_name: str | None,
    handle: str | None,
    distinctive_tokens: Sequence[str] | None = None,
    generic_tokens_extra: Sequence[str] | None = None,
) -> NameSimilarityResult:
    """For social accounts, compute against both display name and handle
    (stripped of domain suffix like .bsky.social) and take the higher score.
    """
    clean_handle: str | None = None
    if handle:
        h = handle.lstrip("@").strip()
        parts = h.split(".")
        clean_handle = parts[0] if parts else h

    res_display = (
        calculate_name_similarity(official_name, display_name, distinctive_tokens, generic_tokens_extra)
        if display_name
        else None
    )
    res_handle = (
        calculate_name_similarity(official_name, clean_handle, distinctive_tokens, generic_tokens_extra)
        if clean_handle
        else None
    )

    if res_display and res_handle:
        if res_handle.name_similarity > res_display.name_similarity:
            return res_handle
        return res_display
    elif res_display:
        return res_display
    elif res_handle:
        return res_handle
    else:
        return calculate_name_similarity(official_name, "", distinctive_tokens, generic_tokens_extra)
