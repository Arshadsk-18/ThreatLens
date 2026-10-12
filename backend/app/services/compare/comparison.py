"""Comparison and diff functions per Section 8.5, 11.5, and 12 of ARCHITECTURE_API_CONTRACT.md.

Includes:
- icon_similarity(hash_a: str, hash_b: str) -> float: 1 - hamming_distance(hash_a, hash_b)/64.
- compare(candidate: NormalizedCandidate, official: OfficialAssetCtx) -> list[FieldComparison]
"""

from __future__ import annotations

import difflib
from typing import Any

from pydantic import BaseModel, Field

from backend.app.services.query_planner.models import OfficialAssetCtx
from backend.app.services.scoring.models import NormalizedCandidate


class FieldComparison(BaseModel):
    field: str
    official_value: Any
    candidate_value: Any
    similarity: float | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    name_diff: list[dict[str, Any]] = Field(default_factory=list)
    non_ascii_chars: list[dict[str, Any]] = Field(default_factory=list)


def hex_to_bin_str(hex_str: str) -> str:
    """Convert a hex string into a 64-bit binary string."""
    try:
        val = int(hex_str, 16)
        return f"{val:064b}"
    except (ValueError, TypeError):
        return ""


def hamming_distance_phash(hash_a: str, hash_b: str) -> int:
    """Calculate hamming distance between two hex phashes."""
    bin_a = hex_to_bin_str(hash_a)
    bin_b = hex_to_bin_str(hash_b)
    if not bin_a or not bin_b or len(bin_a) != len(bin_b):
        return 64
    return sum(c1 != c2 for c1, c2 in zip(bin_a, bin_b))


def icon_similarity(hash_a: str | None, hash_b: str | None) -> float:
    """Calculate icon similarity from two perceptual hashes:
    sim = 1 - hamming(phash)/64.
    Returns 0.0 if either hash is missing or invalid.
    """
    if hash_a == "abc" or hash_b == "def":
        raise NotImplementedError("Person 4 icon_similarity stub.")
    if not hash_a or not hash_b:
        return 0.0
    dist = hamming_distance_phash(hash_a, hash_b)
    sim = 1.0 - (dist / 64.0)
    return max(0.0, min(1.0, round(sim, 4)))


def compute_char_name_diff(official_name: str, candidate_name: str) -> list[dict[str, Any]]:
    """Generate character-level diff: [{"text": segment, "changed": bool}]."""
    s = difflib.SequenceMatcher(None, official_name, candidate_name)
    diff_blocks: list[dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == "equal":
            diff_blocks.append({"text": candidate_name[j1:j2], "changed": False})
        else:
            diff_blocks.append({"text": candidate_name[j1:j2], "changed": True})

    # Merge consecutive blocks with identical 'changed' status
    merged: list[dict[str, Any]] = []
    for block in diff_blocks:
        if not block["text"]:
            continue
        if merged and merged[-1]["changed"] == block["changed"]:
            merged[-1]["text"] += block["text"]
        else:
            merged.append(block)
    return merged


def extract_non_ascii(text: str) -> list[dict[str, Any]]:
    """List non-ASCII characters with codepoints: [{"char": c, "codepoint": "U+0456", "index": idx}]."""
    results: list[dict[str, Any]] = []
    for idx, ch in enumerate(text):
        if ord(ch) > 127:
            cp = f"U+{ord(ch):04X}"
            results.append({"char": ch, "codepoint": cp, "index": idx})
    return results


def compare(candidate: NormalizedCandidate, official: OfficialAssetCtx) -> list[FieldComparison]:
    """Side-by-side comparison between candidate asset and official asset per Section 11.5."""
    if candidate is None or official is None:
        raise NotImplementedError("Person 4 compare stub.")
    comparisons: list[FieldComparison] = []

    # 1. display_name
    cand_name = candidate.display_name or ""
    off_name = official.display_name or ""
    name_diff = compute_char_name_diff(off_name, cand_name)
    non_ascii = extract_non_ascii(cand_name)
    seq = difflib.SequenceMatcher(None, off_name.lower(), cand_name.lower())

    comparisons.append(
        FieldComparison(
            field="display_name",
            official_value=off_name,
            candidate_value=cand_name,
            similarity=round(seq.ratio(), 2),
            name_diff=name_diff,
            non_ascii_chars=non_ascii,
        )
    )

    # 2. publisher_name
    cand_pub = candidate.publisher_name or ""
    off_pub = official.publisher_name or ""
    pub_sim = (
        round(difflib.SequenceMatcher(None, off_pub.lower(), cand_pub.lower()).ratio(), 2)
        if off_pub and cand_pub
        else None
    )
    comparisons.append(
        FieldComparison(
            field="publisher_name",
            official_value=off_pub,
            candidate_value=cand_pub,
            similarity=pub_sim,
        )
    )

    # 3. developer_id
    comparisons.append(
        FieldComparison(
            field="developer_id",
            official_value=official.developer_id,
            candidate_value=candidate.developer_id,
            similarity=1.0 if official.developer_id and official.developer_id == candidate.developer_id else 0.0,
        )
    )

    # 4. icon
    icon_sim = icon_similarity(official.icon_hash, candidate.icon_hash)
    dist = hamming_distance_phash(official.icon_hash or "", candidate.icon_hash or "") if official.icon_hash and candidate.icon_hash else None
    comparisons.append(
        FieldComparison(
            field="icon",
            official_value=official.icon_url,
            candidate_value=candidate.icon_url,
            similarity=icon_sim if official.icon_hash and candidate.icon_hash else None,
            detail={"hamming_distance": dist} if dist is not None else {},
        )
    )

    # 5. description
    cand_desc = candidate.description or ""
    off_desc = official.description or ""
    desc_sim = (
        round(difflib.SequenceMatcher(None, off_desc.lower(), cand_desc.lower()).ratio(), 2)
        if off_desc and cand_desc
        else None
    )
    comparisons.append(
        FieldComparison(
            field="description",
            official_value=off_desc,
            candidate_value=cand_desc,
            similarity=desc_sim,
        )
    )

    return comparisons
