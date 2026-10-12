"""Tests for golden test vectors in name_vectors.json per Section 8.1 and 8.6."""

import json
from pathlib import Path

import pytest

from backend.app.services.normalization.name_similarity import calculate_name_similarity

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "name_vectors.json"


@pytest.fixture
def name_vectors():
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_name_similarity_vectors_count(name_vectors):
    """Ensure at least 40+ vectors are defined."""
    assert len(name_vectors) >= 40, f"Expected 40+ vectors, found {len(name_vectors)}"


def test_name_similarity_vectors(name_vectors):
    """Validate all golden test vectors against reference name similarity calculation."""
    for vector in name_vectors:
        result = calculate_name_similarity(
            official_name=vector["brand_name"],
            candidate_name=vector["candidate_name"],
            distinctive_tokens=vector.get("distinctive_tokens"),
            generic_tokens_extra=vector.get("generic_tokens_extra"),
        )
        assert result.name_similarity == vector["expected_similarity"], (
            f"Vector {vector['id']} ({vector['candidate_name']}): "
            f"expected similarity {vector['expected_similarity']}, got {result.name_similarity}"
        )


def test_section_8_6_worked_examples():
    """Verify worked examples directly described in Section 8.6 of ARCHITECTURE_API_CONTRACT.md."""
    # Kaveri Bank -> 1.00
    res_exact = calculate_name_similarity("Kaveri Bank", "Kaveri Bank")
    assert res_exact.name_similarity == 1.00

    # Kaveri Bank Rewards -> ~0.85 (exact reference token_score: 0.86)
    res_rewards = calculate_name_similarity(
        "Kaveri Bank", "Kaveri Bank Rewards", distinctive_tokens=["kaveri"]
    )
    assert res_rewards.name_similarity == 0.86

    # Kaveri Coffee Roasters -> ~0.63 (exact reference token_score: 0.62) passes G1 (>= 0.60)
    res_coffee = calculate_name_similarity(
        "Kaveri Bank", "Kaveri Coffee Roasters", distinctive_tokens=["kaveri"]
    )
    assert res_coffee.name_similarity == 0.62
    assert res_coffee.name_similarity >= 0.60

    # Coffee Roasters -> < 0.60 (fails G1)
    res_roasters = calculate_name_similarity(
        "Kaveri Bank", "Coffee Roasters", distinctive_tokens=["kaveri"]
    )
    assert res_roasters.name_similarity == 0.25
    assert res_roasters.name_similarity < 0.60

    # KaveriBnak -> character swap similarity
    res_bnak = calculate_name_similarity("Kaveri Bank", "KaveriBnak")
    assert res_bnak.name_similarity == 0.90

    # Kav eri Bank -> spacing similarity 1.00
    res_space = calculate_name_similarity("Kaveri Bank", "Kav eri Bank")
    assert res_space.name_similarity == 1.00
