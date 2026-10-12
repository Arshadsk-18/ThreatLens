"""Tests for LookalikeTechnique classification per Section 8.1 and 8.6."""

import json
from pathlib import Path

import pytest

from backend.app.services.normalization.techniques import (
    LookalikeTechnique,
    classify_technique,
)

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "name_vectors.json"


@pytest.fixture
def name_vectors():
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_lookalike_techniques_vectors(name_vectors):
    """Validate lookalike technique classification for all test vectors in name_vectors.json."""
    for vector in name_vectors:
        technique, metadata = classify_technique(
            observed=vector["candidate_name"],
            official=vector["brand_name"],
        )
        assert technique.value == vector["expected_technique"], (
            f"Vector {vector['id']} ({vector['candidate_name']}): "
            f"expected {vector['expected_technique']}, got {technique.value}"
        )
        assert metadata["observed"] == vector["candidate_name"]
        assert metadata["official"] == vector["brand_name"]


def test_all_techniques_covered(name_vectors):
    """Verify that every LookalikeTechnique enum variant is tested."""
    found = {v["expected_technique"] for v in name_vectors}
    expected = {t.value for t in LookalikeTechnique}
    missing = expected - found
    assert not missing, f"Missing tests for techniques: {missing}"


def test_technique_priority_order():
    """Verify exact priority order:
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
    # Exact match with casing differences should be EXACT_NAME_REUSE
    t, m = classify_technique("kaveri bank", "Kaveri Bank")
    assert t == LookalikeTechnique.EXACT_NAME_REUSE

    # Homoglyph beats spacing/repetition
    t, m = classify_technique("Kaver\u0456 Bank", "Kaveri Bank")
    assert t == LookalikeTechnique.HOMOGLYPH
    assert m.get("homoglyph_detected") is True

    # Character swap: KaveriBnak
    t, m = classify_technique("KaveriBnak", "Kaveri Bank")
    assert t == LookalikeTechnique.CHARACTER_SWAP

    # Omission: Kaver Bank
    t, m = classify_technique("Kaver Bank", "Kaveri Bank")
    assert t == LookalikeTechnique.OMISSION

    # Repetition: Kaverri Bank / Kaveri Bankk
    t, m = classify_technique("Kaveri Bankk", "Kaveri Bank")
    assert t == LookalikeTechnique.REPETITION

    # Keyboard adjacent: Kaveri Vank (b -> v)
    t, m = classify_technique("Kaveri Vank", "Kaveri Bank")
    assert t == LookalikeTechnique.KEYBOARD_ADJACENT

    # Added word: Kaveri Bank Rewards
    t, m = classify_technique("Kaveri Bank Rewards", "Kaveri Bank")
    assert t == LookalikeTechnique.ADDED_WORD

    # Spacing: Kav eri Bank
    t, m = classify_technique("Kav eri Bank", "Kaveri Bank")
    assert t == LookalikeTechnique.SPACING

    # Separator: Kaveri-Bank
    t, m = classify_technique("Kaveri-Bank", "Kaveri Bank")
    assert t == LookalikeTechnique.SEPARATOR

    # None: Coffee Roasters
    t, m = classify_technique("Coffee Roasters", "Kaveri Bank")
    assert t == LookalikeTechnique.NONE
