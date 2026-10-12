"""Lookalike technique classification per Section 8.1 and Section 8.6.

Precedence order:
1. EXACT_NAME_REUSE
2. HOMOGLYPH
3. CHARACTER_SWAP
4. OMISSION
5. REPETITION
6. KEYBOARD_ADJACENT
7. ADDED_WORD
8. SPACING
9. SEPARATOR
10. NONE
"""

from enum import Enum
from typing import Any

from app.services.normalization.name_similarity import normalize_name


class LookalikeTechnique(str, Enum):
    EXACT_NAME_REUSE = "EXACT_NAME_REUSE"
    HOMOGLYPH = "HOMOGLYPH"
    CHARACTER_SWAP = "CHARACTER_SWAP"
    OMISSION = "OMISSION"
    REPETITION = "REPETITION"
    KEYBOARD_ADJACENT = "KEYBOARD_ADJACENT"
    ADDED_WORD = "ADDED_WORD"
    SPACING = "SPACING"
    SEPARATOR = "SEPARATOR"
    NONE = "NONE"


KEYBOARD_ADJACENCY: dict[str, set[str]] = {
    "q": {"w", "a", "s", "1", "2"},
    "w": {"q", "e", "a", "s", "d", "2", "3"},
    "e": {"w", "r", "s", "d", "f", "3", "4"},
    "r": {"e", "t", "d", "f", "g", "4", "5"},
    "t": {"r", "y", "f", "g", "h", "5", "6"},
    "y": {"t", "u", "g", "h", "j", "6", "7"},
    "u": {"y", "i", "h", "j", "k", "7", "8"},
    "i": {"u", "o", "j", "k", "l", "8", "9"},
    "o": {"i", "p", "k", "l", "9", "0"},
    "p": {"o", "l", "0", "-"},
    "a": {"q", "w", "s", "z"},
    "s": {"a", "w", "e", "d", "z", "x"},
    "d": {"s", "e", "r", "f", "x", "c"},
    "f": {"d", "r", "t", "g", "c", "v"},
    "g": {"f", "t", "y", "h", "v", "b"},
    "h": {"g", "y", "u", "j", "b", "n"},
    "j": {"h", "u", "i", "k", "n", "m"},
    "k": {"j", "i", "o", "l", "m"},
    "l": {"k", "o", "p"},
    "z": {"a", "s", "x"},
    "x": {"z", "s", "d", "c"},
    "c": {"x", "d", "f", "v"},
    "v": {"c", "f", "g", "b"},
    "b": {"v", "g", "h", "n"},
    "n": {"b", "h", "j", "m"},
    "m": {"n", "j", "k"},
}


def _is_adjacent_char(c1: str, c2: str) -> bool:
    c1_low, c2_low = c1.lower(), c2.lower()
    return c2_low in KEYBOARD_ADJACENCY.get(c1_low, set())


def _check_character_swap(s1: str, s2: str) -> bool:
    """Check if s2 is formed from s1 by a single adjacent character transposition."""
    if len(s1) != len(s2) or len(s1) < 2:
        return False
    diffs = [i for i in range(len(s1)) if s1[i] != s2[i]]
    if len(diffs) == 2:
        i, j = diffs
        if j == i + 1 and s1[i] == s2[j] and s1[j] == s2[i]:
            return True
    return False


def _check_omission(s_orig: str, s_cand: str) -> bool:
    """Check if s_cand has omitted characters from s_orig (1 to 2 omitted chars)."""
    diff_len = len(s_orig) - len(s_cand)
    if not (1 <= diff_len <= 2):
        return False
    it = iter(s_orig)
    return all(c in it for c in s_cand)


def _check_repetition(s_orig: str, s_cand: str) -> bool:
    """Check if s_cand has repeated characters from s_orig (e.g. kaverri, kaveri bankk)."""
    diff_len = len(s_cand) - len(s_orig)
    if diff_len <= 0:
        return False
    i, j = 0, 0
    extra = 0
    while i < len(s_orig) and j < len(s_cand):
        if s_orig[i] == s_cand[j]:
            i += 1
            j += 1
        elif j > 0 and s_cand[j] == s_cand[j - 1]:
            j += 1
            extra += 1
        else:
            return False
    while j < len(s_cand) and j > 0 and s_cand[j] == s_cand[j - 1]:
        j += 1
        extra += 1
    return i == len(s_orig) and j == len(s_cand) and extra == diff_len


def _check_keyboard_adjacent(s1: str, s2: str) -> bool:
    """Check if s2 differs from s1 by 1 or 2 keyboard-adjacent substitutions."""
    if len(s1) != len(s2):
        return False
    diffs = [i for i in range(len(s1)) if s1[i] != s2[i]]
    if 1 <= len(diffs) <= 2:
        return all(_is_adjacent_char(s1[i], s2[i]) for i in diffs)
    return False


def _check_added_word(tokens_orig: list[str], tokens_cand: list[str]) -> bool:
    """Check if tokens_cand contains all tokens of tokens_orig plus 1+ extra words."""
    if len(tokens_cand) <= len(tokens_orig):
        return False
    it = iter(tokens_cand)
    return all(t in it for t in tokens_orig)


def classify_technique(observed: str, official: str) -> tuple[LookalikeTechnique, dict[str, Any]]:
    """Classify the look-alike technique in exact contract priority order:
    1. EXACT_NAME_REUSE
    2. HOMOGLYPH
    3. CHARACTER_SWAP
    4. OMISSION
    5. REPETITION
    6. KEYBOARD_ADJACENT
    7. ADDED_WORD
    8. SPACING
    9. SEPARATOR
    10. NONE

    Returns:
        tuple[LookalikeTechnique, dict]: The classified technique and metadata dictionary.
    """
    metadata: dict[str, Any] = {
        "observed": observed,
        "official": official,
    }

    raw_obs_clean = observed.strip()
    raw_off_clean = official.strip()

    # 1. EXACT_NAME_REUSE: raw strings match (case-insensitive)
    if raw_obs_clean.lower() == raw_off_clean.lower():
        metadata["matched_rule"] = "EXACT_NAME_REUSE"
        return LookalikeTechnique.EXACT_NAME_REUSE, metadata

    # Normalize both strings
    norm_obs, obs_homo = normalize_name(observed)
    norm_off, _off_homo = normalize_name(official)

    metadata["normalized_observed"] = norm_obs
    metadata["normalized_official"] = norm_off

    # 2. HOMOGLYPH: homoglyphs mapped in observed candidate
    if obs_homo:
        metadata["matched_rule"] = "HOMOGLYPH"
        metadata["homoglyph_detected"] = True
        return LookalikeTechnique.HOMOGLYPH, metadata

    # Clean alphanumeric strings without spaces
    clean_obs_nospace = "".join(c for c in norm_obs if c.isalnum())
    clean_off_nospace = "".join(c for c in norm_off if c.isalnum())

    # 3. CHARACTER_SWAP: adjacent character transposition
    if (
        clean_obs_nospace
        and clean_off_nospace
        and clean_obs_nospace != clean_off_nospace
        and _check_character_swap(clean_off_nospace, clean_obs_nospace)
    ):
        metadata["matched_rule"] = "CHARACTER_SWAP"
        return LookalikeTechnique.CHARACTER_SWAP, metadata

    # 4. OMISSION: missing characters from official name
    if (
        clean_obs_nospace
        and clean_off_nospace
        and clean_obs_nospace != clean_off_nospace
        and _check_omission(clean_off_nospace, clean_obs_nospace)
    ):
        metadata["matched_rule"] = "OMISSION"
        return LookalikeTechnique.OMISSION, metadata

    # 5. REPETITION: repeated/doubled characters
    if (
        clean_obs_nospace
        and clean_off_nospace
        and clean_obs_nospace != clean_off_nospace
        and _check_repetition(clean_off_nospace, clean_obs_nospace)
    ):
        metadata["matched_rule"] = "REPETITION"
        return LookalikeTechnique.REPETITION, metadata

    # 6. KEYBOARD_ADJACENT: keyboard typos / adjacent substitutions
    if (
        clean_obs_nospace
        and clean_off_nospace
        and clean_obs_nospace != clean_off_nospace
        and _check_keyboard_adjacent(clean_off_nospace, clean_obs_nospace)
    ):
        metadata["matched_rule"] = "KEYBOARD_ADJACENT"
        return LookalikeTechnique.KEYBOARD_ADJACENT, metadata

    # 7. ADDED_WORD: additional word added
    tokens_off = [t for t in norm_off.split() if t]
    tokens_obs = [t for t in norm_obs.split() if t]
    if _check_added_word(tokens_off, tokens_obs):
        metadata["matched_rule"] = "ADDED_WORD"
        return LookalikeTechnique.ADDED_WORD, metadata

    # 8. SPACING: only difference is internal whitespace spacing (no separators in raw strings)
    if clean_obs_nospace == clean_off_nospace:
        has_sep = any(c in "-_./" for c in observed) or any(c in "-_./" for c in official)
        if not has_sep and (norm_obs != norm_off or raw_obs_clean != raw_off_clean):
            metadata["matched_rule"] = "SPACING"
            return LookalikeTechnique.SPACING, metadata

    # 9. SEPARATOR: separators (-_./) used
    has_sep = any(c in "-_./" for c in observed) or any(c in "-_./" for c in official)
    if has_sep and clean_obs_nospace == clean_off_nospace:
        metadata["matched_rule"] = "SEPARATOR"
        return LookalikeTechnique.SEPARATOR, metadata

    # Check if spacing applies
    if clean_obs_nospace == clean_off_nospace and (norm_obs != norm_off or raw_obs_clean != raw_off_clean):
        metadata["matched_rule"] = "SPACING"
        return LookalikeTechnique.SPACING, metadata

    metadata["matched_rule"] = "NONE"
    return LookalikeTechnique.NONE, metadata
