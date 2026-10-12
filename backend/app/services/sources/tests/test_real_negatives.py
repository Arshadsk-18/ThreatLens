"""Unit and dataset integrity tests for Real Negatives capture and dual verification.

Owner: Person 3 (backend/app/services/sources/tests/test_real_negatives.py)
Reference: Contract Section 5.6, 12, 14, Appendix B
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from app.schemas import NormalizedCandidate
from app.services.sources.apple import AppleItunesAdapter
from app.services.sources.bluesky import BlueskyPublicAdapter
from app.services.sources.capture import capture_candidates, load_existing_candidates
from app.services.sources.verify_negatives import (
    export_verified_records,
    is_record_double_verified,
    verify_candidate_record,
)

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "tests" / "fixtures"
REAL_NEGATIVES_DIR = FIXTURES_DIR / "real_negatives"
CANDIDATES_FILE = REAL_NEGATIVES_DIR / "candidates.jsonl"
VERIFIED_FILE = REAL_NEGATIVES_DIR / "verified.jsonl"
LOOKALIKES_FILE = FIXTURES_DIR / "recorded" / "benign_lookalikes.json"


@pytest.mark.asyncio
@respx.mock
async def test_capture_writes_valid_normalized_candidate_records(
    tmp_path: Path,
) -> None:
    """Capture script queries adapters and writes valid NormalizedCandidate records."""
    # Mock Apple
    apple_fixture = {
        "resultCount": 1,
        "results": [
            {
                "trackId": 99887766,
                "trackName": "Kaveri Express App",
                "bundleId": "com.kaveri.express",
                "sellerName": "Kaveri Express Logistics",
                "artistId": 554433,
                "description": "Bus tickets booking app.",
                "primaryGenreName": "Travel",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/icon.jpg",
                "releaseDate": "2024-01-01T00:00:00Z",
                "trackViewUrl": "https://apps.apple.com/in/app/kaveri-express/id99887766",
            }
        ],
    }
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(200, json=apple_fixture)
    )

    # Mock Bluesky
    bsky_actor_fixture = {
        "actors": [
            {
                "did": "did:plc:kaveritrust998877",
                "handle": "kaveritrust.bsky.social",
                "displayName": "Kaveri River Trust",
                "description": "Clean river initiative.",
            }
        ]
    }
    bsky_profile_fixture = {
        "profiles": [
            {
                "did": "did:plc:kaveritrust998877",
                "handle": "kaveritrust.bsky.social",
                "displayName": "Kaveri River Trust",
                "description": "Clean river initiative.",
                "followersCount": 100,
                "followsCount": 10,
                "postsCount": 5,
            }
        ]
    }
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(200, json=bsky_actor_fixture)
    )
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(200, json=bsky_profile_fixture)
    )

    out_file = tmp_path / "candidates.jsonl"
    apple_adapter = AppleItunesAdapter()
    bluesky_adapter = BlueskyPublicAdapter()

    records = await capture_candidates(
        output_file=out_file,
        terms=["kaveri express"],
        apple_adapter=apple_adapter,
        bluesky_adapter=bluesky_adapter,
    )

    assert len(records) == 2
    assert out_file.exists()

    for rec in records:
        assert rec["provenance"] == "REAL_CAPTURED"
        assert rec["case_ref"].startswith("rn-")
        assert rec["proposed_label"] == "BENIGN_NAMESAKE"
        # Must validate against contract NormalizedCandidate schema
        cand_obj = NormalizedCandidate(**rec["candidate"])
        assert cand_obj.stable_identifier in ("99887766", "did:plc:kaveritrust998877")


def test_verified_jsonl_excludes_invalid_verifications(tmp_path: Path) -> None:
    """Records with one verifier, equal verifiers, or disagreement are excluded from verified.jsonl."""
    # 1. Valid record (two distinct verifiers agreeing on BENIGN_NAMESAKE)
    valid_rec = {
        "case_ref": "rn-0001",
        "source_id": "apple_itunes",
        "candidate": {"stable_identifier": "id-1", "display_name": "Valid App"},
    }
    verify_candidate_record(valid_rec, "analyst_1", "BENIGN_NAMESAKE", "Legit namesake")
    verify_candidate_record(valid_rec, "analyst_2", "BENIGN_NAMESAKE", "Confirmed")
    assert is_record_double_verified(valid_rec) is True

    # 2. Equal verifiers (verifier_1 == verifier_2) MUST raise ValueError
    self_verify_rec = {
        "case_ref": "rn-0002",
        "source_id": "apple_itunes",
        "candidate": {"stable_identifier": "id-2", "display_name": "Self Verified"},
    }
    verify_candidate_record(self_verify_rec, "analyst_1", "BENIGN_NAMESAKE")
    with pytest.raises(ValueError) as exc:
        verify_candidate_record(self_verify_rec, "analyst_1", "BENIGN_NAMESAKE")
    assert "cannot be the same" in str(exc.value)
    assert is_record_double_verified(self_verify_rec) is False

    # 3. Disagreement (analyst_1 = BENIGN_NAMESAKE, analyst_2 = NEEDS_REVIEW)
    disagree_rec = {
        "case_ref": "rn-0003",
        "source_id": "apple_itunes",
        "candidate": {"stable_identifier": "id-3", "display_name": "Disputed App"},
    }
    verify_candidate_record(disagree_rec, "analyst_1", "BENIGN_NAMESAKE")
    verify_candidate_record(disagree_rec, "analyst_2", "NEEDS_REVIEW")
    assert is_record_double_verified(disagree_rec) is False

    # 4. Only one verifier
    single_rec = {
        "case_ref": "rn-0004",
        "source_id": "apple_itunes",
        "candidate": {"stable_identifier": "id-4", "display_name": "Single Review"},
    }
    verify_candidate_record(single_rec, "analyst_1", "BENIGN_NAMESAKE")
    assert is_record_double_verified(single_rec) is False

    # Write test candidates file
    cand_file = tmp_path / "candidates.jsonl"
    ver_file = tmp_path / "verified.jsonl"
    with open(cand_file, "w", encoding="utf-8") as f:
        f.writelines(
            json.dumps(r) + "\n"
            for r in [valid_rec, self_verify_rec, disagree_rec, single_rec]
        )

    exported = export_verified_records(cand_file, ver_file)
    assert len(exported) == 1
    assert exported[0]["case_ref"] == "rn-0001"


def test_jsonl_round_trips() -> None:
    """All stored JSONL candidate and verified records round-trip perfectly."""
    for file_path in [CANDIDATES_FILE, VERIFIED_FILE]:
        assert file_path.exists(), f"Missing dataset file {file_path}"
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        assert len(lines) > 0
        for line in lines:
            data = json.loads(line)
            serialized = json.dumps(data, ensure_ascii=False)
            re_parsed = json.loads(serialized)
            assert re_parsed["case_ref"] == data["case_ref"]
            assert re_parsed["source_id"] == data["source_id"]

            # Candidate must round-trip into schema
            cand = NormalizedCandidate(**data["candidate"])
            assert cand.stable_identifier == data["candidate"]["stable_identifier"]


@pytest.mark.asyncio
@respx.mock
async def test_running_capture_twice_does_not_duplicate_case_refs(
    tmp_path: Path,
) -> None:
    """Repeated capture runs do not duplicate entries; stable key = (source_id, stable_identifier)."""
    apple_fixture = {
        "resultCount": 1,
        "results": [
            {
                "trackId": 1234567,
                "trackName": "Kaveri Silks",
                "bundleId": "com.kaveri.silks",
                "sellerName": "Kaveri Silks",
                "artistId": 1122,
                "primaryGenreName": "Shopping",
                "artworkUrl100": "https://is1-ssl.mzstatic.com/icon.jpg",
                "releaseDate": "2024-01-01T00:00:00Z",
                "trackViewUrl": "https://apps.apple.com/in/app/kaveri-silks/id1234567",
            }
        ],
    }
    respx.get("https://itunes.apple.com/search").mock(
        return_value=httpx.Response(200, json=apple_fixture)
    )
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors").mock(
        return_value=httpx.Response(200, json={"actors": []})
    )

    out_file = tmp_path / "candidates.jsonl"
    apple = AppleItunesAdapter()
    bsky = BlueskyPublicAdapter()

    # Run 1
    recs1 = await capture_candidates(
        output_file=out_file,
        terms=["kaveri silks"],
        apple_adapter=apple,
        bluesky_adapter=bsky,
    )
    assert len(recs1) == 1
    assert recs1[0]["case_ref"] == "rn-0001"

    # Run 2
    recs2 = await capture_candidates(
        output_file=out_file,
        terms=["kaveri silks"],
        apple_adapter=apple,
        bluesky_adapter=bsky,
    )
    assert len(recs2) == 1
    assert recs2[0]["case_ref"] == "rn-0001"

    # Map verification
    mapping, max_idx = load_existing_candidates(out_file)
    assert len(mapping) == 1
    assert max_idx == 1
    assert ("apple_itunes", "1234567") in mapping


def test_verified_negatives_dataset_integrity_and_lookalikes() -> None:
    """Verify target size (60+ verified), verifier agreement, and 14 DEMO lookalikes."""
    with open(VERIFIED_FILE, "r", encoding="utf-8") as f:
        verified_records = [json.loads(line.strip()) for line in f if line.strip()]

    # Must meet or exceed target of 60+ verified records
    assert len(verified_records) >= 60

    # Ensure every single record satisfies dual-verifier contract
    for rec in verified_records:
        ver = rec["verification"]
        assert ver["verifier_1"] is not None
        assert ver["verifier_2"] is not None
        assert ver["verifier_1"] != ver["verifier_2"]
        assert ver["verifier_1_label"] == "BENIGN_NAMESAKE"
        assert ver["verifier_2_label"] == "BENIGN_NAMESAKE"
        assert ver["verified_at"] is not None

    # Check 14 tagged DEMO lookalikes
    lookalikes = [r for r in verified_records if r.get("demo_lookalike") is True]
    assert len(lookalikes) == 14

    # Verify recorded/benign_lookalikes.json exists and contains 14 records
    assert LOOKALIKES_FILE.exists()
    lookalike_data = json.loads(LOOKALIKES_FILE.read_text(encoding="utf-8"))
    assert len(lookalike_data["records"]) == 14
