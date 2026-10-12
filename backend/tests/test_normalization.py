"""Unit tests for ThreatLens v3 name normalization and look-alike techniques.

Validates:
- Section 8.1 Name normalization reference formula
- Section 8.6 Worked examples
- Section 8.7 Scoring walkthroughs
- Golden test vectors in backend/tests/fixtures/name_vectors.json
- test_name_similarity_vectors and test_lookalike_techniques (Must-pass automated tests from 18.3)
"""

import json
from pathlib import Path

import pytest

from backend.app.services.normalization.normalizer import (
    compute_name_similarity,
    compute_social_name_similarity,
    normalize_name,
)
from backend.app.services.normalization.technique import (
    LookalikeTechnique,
    classify_technique,
)

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "name_vectors.json"


@pytest.fixture
def name_vectors():
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_name_similarity_vectors(name_vectors):
    """Validate all 40+ name test vectors against reference formula."""
    assert len(name_vectors) >= 40, f"Expected 40+ vectors, got {len(name_vectors)}"

    for vector in name_vectors:
        result = compute_name_similarity(
            brand_name=vector["brand_name"],
            candidate_name=vector["candidate_name"],
            distinctive_tokens=vector.get("distinctive_tokens"),
            generic_tokens_extra=vector.get("generic_tokens_extra"),
        )
        assert result.name_similarity == vector["expected_similarity"], (
            f"Failed on vector {vector['id']} ({vector['candidate_name']}): "
            f"expected similarity {vector['expected_similarity']}, got {result.name_similarity}"
        )


def test_lookalike_techniques(name_vectors):
    """Validate that technique classification matches the expected LookalikeTechnique."""
    covered_techniques = set()

    for vector in name_vectors:
        result = compute_name_similarity(
            brand_name=vector["brand_name"],
            candidate_name=vector["candidate_name"],
            distinctive_tokens=vector.get("distinctive_tokens"),
            generic_tokens_extra=vector.get("generic_tokens_extra"),
        )
        expected_technique = vector["expected_technique"]
        assert result.technique.value == expected_technique, (
            f"Failed on vector {vector['id']} ({vector['candidate_name']}): "
            f"expected {expected_technique}, got {result.technique.value}"
        )
        covered_techniques.add(result.technique.value)

    # Check that all 10 LookalikeTechnique values are covered
    expected_all = {t.value for t in LookalikeTechnique}
    assert expected_all.issubset(covered_techniques), (
        f"Missing coverage for techniques: {expected_all - covered_techniques}"
    )


def test_contract_section_8_6_worked_examples():
    """Verify worked examples directly described in Section 8.6 of the contract."""
    # 1. Exact name reuse
    res_exact = compute_name_similarity("Kaveri Bank", "Kaveri Bank")
    assert res_exact.technique == LookalikeTechnique.EXACT_NAME_REUSE
    assert res_exact.name_similarity == 1.0

    # 2. Cyrillic homoglyph
    res_homo = compute_name_similarity("Kaveri Bank", "Kaver\u0456 Bank")
    assert res_homo.technique == LookalikeTechnique.HOMOGLYPH
    assert res_homo.homoglyph_detected is True
    assert res_homo.name_similarity == 1.0

    # 3. Spacing variants: 'Kaveri  Bank' or 'Kav eri Bank'
    res_space1 = compute_name_similarity("Kaveri Bank", "Kaveri  Bank")
    assert res_space1.technique == LookalikeTechnique.SPACING
    assert res_space1.name_similarity == 1.0

    res_space2 = compute_name_similarity("Kaveri Bank", "Kav eri Bank")
    assert res_space2.technique == LookalikeTechnique.SPACING
    assert res_space2.name_similarity == 1.0

    # 4. Character swap: 'KaveriBnak'
    res_swap = compute_name_similarity("Kaveri Bank", "KaveriBnak")
    assert res_swap.technique == LookalikeTechnique.CHARACTER_SWAP
    assert res_swap.name_similarity == 0.90

    # 5. Added word: 'Kaveri Bank Rewards'
    res_added = compute_name_similarity("Kaveri Bank", "Kaveri Bank Rewards", distinctive_tokens=["kaveri"])
    assert res_added.technique == LookalikeTechnique.ADDED_WORD
    assert res_added.name_similarity == 0.86

    # 6. Benign namesake: 'Kaveri Coffee Roasters'
    res_benign = compute_name_similarity("Kaveri Bank", "Kaveri Coffee Roasters", distinctive_tokens=["kaveri"])
    assert res_benign.technique == LookalikeTechnique.NONE
    assert res_benign.name_similarity == 0.62  # passes G1 >= 0.60

    # 7. Unrelated namesake: 'Coffee Roasters'
    res_unrelated = compute_name_similarity("Kaveri Bank", "Coffee Roasters", distinctive_tokens=["kaveri"])
    assert res_unrelated.technique == LookalikeTechnique.NONE
    assert res_unrelated.name_similarity == 0.25  # fails G1 < 0.60


def test_social_name_similarity():
    """Verify social account similarity checks against both display name and handle (stripped of domain suffix)."""
    # Candidate with display name 'Kaveri Bank Rewards' and handle 'kaveri_bank.bsky.social'
    res = compute_social_name_similarity(
        brand_name="Kaveri Bank",
        display_name="Kaveri Bank Rewards",
        handle="kaveribank.bsky.social",
        distinctive_tokens=["kaveri"],
    )
    # The handle stripped gives 'kaveribank' which has similarity 1.0
    assert res.name_similarity == 1.0

    # Fan page scenario from 8.7: display name 'Kaveri Bank Fans', handle 'kaverifans.bsky.social'
    res_fan = compute_social_name_similarity(
        brand_name="Kaveri Bank",
        display_name="Kaveri Bank Fans",
        handle="kaverifans.bsky.social",
        distinctive_tokens=["kaveri"],
    )
    assert res_fan.name_similarity == 0.86
    assert res_fan.technique == LookalikeTechnique.ADDED_WORD


def test_technique_priority_order():
    """Verify priority order: EXACT > HOMOGLYPH > SWAP > OMISSION > REPETITION > KEYBOARD > ADDED > SPACING > SEPARATOR > NONE."""
    # When both exact and spacing might match, exact wins
    t1 = classify_technique("Kaveri Bank", "kaveri bank", "kaveri bank", "kaveri bank", homoglyph_detected=False)
    assert t1 == LookalikeTechnique.EXACT_NAME_REUSE

    # When homoglyph is present, homoglyph wins over swap or spacing
    t2 = classify_technique("Kaveri Bank", "Kaver\u0456 Bank", "kaveri bank", "kaveri bank", homoglyph_detected=True)
    assert t2 == LookalikeTechnique.HOMOGLYPH


def test_normalization_properties():
    """Verify Unicode NFKC normalization and separator collapsing."""
    norm = normalize_name("Kaveri---Bank_Official.App")
    assert norm.normalized == "kaveri bank official app"
    assert norm.tokens == ["kaveri", "bank", "official", "app"]
    assert norm.has_homoglyph is False
