"""Lookalike technique classifier for ThreatLens v3.

Technique classification (LookalikeTechnique):
Priority order:
1. EXACT_NAME_REUSE
2. HOMOGLYPH
3. CHARACTER_SWAP (adjacent transposition)
4. OMISSION
5. REPETITION
6. KEYBOARD_ADJACENT
7. ADDED_WORD
8. SPACING
9. SEPARATOR
10. NONE
"""

from enum import Enum


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


# Standard QWERTY adjacent keys (lowercase)
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


def is_adjacent_char(c1: str, c2: str) -> bool:
    c1_low, c2_low = c1.lower(), c2.lower()
    return c2_low in KEYBOARD_ADJACENCY.get(c1_low, set())


def check_character_swap(s1: str, s2: str) -> bool:
    """Check if s2 is formed from s1 by a single adjacent character transposition."""
    if len(s1) != len(s2) or len(s1) < 2:
        return False
    diffs = [i for i in range(len(s1)) if s1[i] != s2[i]]
    if len(diffs) == 2:
        i, j = diffs
        if j == i + 1 and s1[i] == s2[j] and s1[j] == s2[i]:
            return True
    return False


def check_omission(s_orig: str, s_cand: str) -> bool:
    """Check if s_cand has omitted characters from s_orig (1 to 2 omitted chars)."""
    diff_len = len(s_orig) - len(s_cand)
    if not (1 <= diff_len <= 2):
        return False
    # Check if s_cand is a subsequence of s_orig
    it = iter(s_orig)
    return all(c in it for c in s_cand)


def check_repetition(s_orig: str, s_cand: str) -> bool:
    """Check if s_cand has repeated characters from s_orig (e.g. kaaveri, kaaverii)."""
    diff_len = len(s_cand) - len(s_orig)
    if diff_len <= 0:
        return False
    # Check if s_cand can be collapsed or reduced by removing runs of identical consecutive chars
    # Character by character matching where extra chars must duplicate the preceding char
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


def check_keyboard_adjacent(s1: str, s2: str) -> bool:
    """Check if s2 differs from s1 by 1 or 2 keyboard-adjacent substitutions."""
    if len(s1) != len(s2):
        return False
    diffs = [i for i in range(len(s1)) if s1[i] != s2[i]]
    if 1 <= len(diffs) <= 2:
        return all(is_adjacent_char(s1[i], s2[i]) for i in diffs)
    return False


def check_added_word(tokens_orig: list[str], tokens_cand: list[str]) -> bool:
    """Check if tokens_cand contains all tokens of tokens_orig plus 1+ extra words."""
    if len(tokens_cand) <= len(tokens_orig):
        return False
    # Check if all tokens_orig appear in tokens_cand preserving order or as subset
    it = iter(tokens_cand)
    return all(t in it for t in tokens_orig)


def classify_technique(
    raw_official: str,
    raw_candidate: str,
    norm_official: str,
    norm_candidate: str,
    homoglyph_detected: bool,
) -> LookalikeTechnique:
    """Classify look-alike technique in exact contract priority order.

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
    # 1. EXACT_NAME_REUSE: raw strings match (case-insensitive after strip)
    if raw_official.strip().lower() == raw_candidate.strip().lower():
        return LookalikeTechnique.EXACT_NAME_REUSE

    # 2. HOMOGLYPH: homoglyph replacement was executed
    if homoglyph_detected:
        return LookalikeTechnique.HOMOGLYPH

    # Normalized versions without spaces & separators for char-level tests
    clean_orig_nospace = "".join(c for c in norm_official if c.isalnum())
    clean_cand_nospace = "".join(c for c in norm_candidate if c.isalnum())

    # 3. CHARACTER_SWAP: adjacent character swap/transposition
    # Test on full string (space-collapsed) or token-by-token
    if (
        clean_orig_nospace
        and clean_cand_nospace
        and clean_orig_nospace != clean_cand_nospace
        and check_character_swap(clean_orig_nospace, clean_cand_nospace)
    ):
        return LookalikeTechnique.CHARACTER_SWAP

    # 4. OMISSION: missing characters from official name
    if (
        clean_orig_nospace
        and clean_cand_nospace
        and clean_orig_nospace != clean_cand_nospace
        and check_omission(clean_orig_nospace, clean_cand_nospace)
    ):
        return LookalikeTechnique.OMISSION

    # 5. REPETITION: repeated/doubled characters
    if (
        clean_orig_nospace
        and clean_cand_nospace
        and clean_orig_nospace != clean_cand_nospace
        and check_repetition(clean_orig_nospace, clean_cand_nospace)
    ):
        return LookalikeTechnique.REPETITION

    # 6. KEYBOARD_ADJACENT: keyboard typos / adjacent substitutions
    if (
        clean_orig_nospace
        and clean_cand_nospace
        and clean_orig_nospace != clean_cand_nospace
        and check_keyboard_adjacent(clean_orig_nospace, clean_cand_nospace)
    ):
        return LookalikeTechnique.KEYBOARD_ADJACENT

    # 7. ADDED_WORD: added tokens
    tokens_orig = [t for t in norm_official.split() if t]
    tokens_cand = [t for t in norm_candidate.split() if t]
    if check_added_word(tokens_orig, tokens_cand):
        return LookalikeTechnique.ADDED_WORD

    # 8. SPACING: only difference is internal whitespace spacing (no separators in raw strings)
    if clean_orig_nospace == clean_cand_nospace:
        has_sep = any(c in "-_./" for c in raw_candidate) or any(c in "-_./" for c in raw_official)
        if not has_sep and (norm_official != norm_candidate or raw_official != raw_candidate):
            return LookalikeTechnique.SPACING

    # 9. SEPARATOR: separators like -_. were used instead of or in addition to spaces
    has_sep = any(c in "-_./" for c in raw_candidate) or any(c in "-_./" for c in raw_official)
    if has_sep and clean_orig_nospace == clean_cand_nospace:
        return LookalikeTechnique.SEPARATOR

    # Check if spacing also applied
    if clean_orig_nospace == clean_cand_nospace and (norm_official != norm_candidate or raw_official != raw_candidate):
        return LookalikeTechnique.SPACING

    return LookalikeTechnique.NONE
