"""Dual-verifier labeling tool and verified dataset generator.

Owner: Person 3 (backend/app/services/sources/verify_negatives.py)
Reference: Contract Section 14, Appendix B

Verification Contract:
A candidate record is verified ONLY when two DIFFERENT verifier names agree
on BENIGN_NAMESAKE. Disagreement or NEEDS_REVIEW stays unverified.
Attempts where verifier_1 == verifier_2 are strictly rejected.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("threatlens.verify")

REPO_ROOT = Path(__file__).resolve().parents[4]
REAL_NEGATIVES_DIR = REPO_ROOT / "backend" / "tests" / "fixtures" / "real_negatives"
CANDIDATES_FILE = REAL_NEGATIVES_DIR / "candidates.jsonl"
VERIFIED_FILE = REAL_NEGATIVES_DIR / "verified.jsonl"


def verify_candidate_record(
    record: dict[str, Any],
    verifier_name: str,
    label: str,
    notes: str = "",
) -> dict[str, Any]:
    """Apply a verifier review to a candidate record adhering to dual-verifier contract.

    Raises ValueError if verifier_2 is the same as verifier_1.
    """
    v_clean = verifier_name.strip()
    if not v_clean:
        raise ValueError("Verifier name must not be empty.")

    lbl = label.strip().upper()
    if lbl not in ("BENIGN_NAMESAKE", "NEEDS_REVIEW", "REJECT"):
        raise ValueError(f"Invalid verification label: {lbl}")

    ver = record.setdefault(
        "verification",
        {"verifier_1": None, "verifier_2": None, "verified_at": None, "notes": ""},
    )

    if ver.get("verifier_1") is None:
        ver["verifier_1"] = v_clean
        ver["verifier_1_label"] = lbl
        ver["notes"] = notes.strip()
    elif ver.get("verifier_2") is None:
        if v_clean == ver["verifier_1"]:
            raise ValueError(
                f"Second verifier '{v_clean}' cannot be the same as first verifier."
            )

        ver["verifier_2"] = v_clean
        ver["verifier_2_label"] = lbl
        if notes.strip():
            existing_note = ver.get("notes", "")
            ver["notes"] = (
                f"{existing_note}; {notes.strip()}" if existing_note else notes.strip()
            )

        # Both verifiers must agree on BENIGN_NAMESAKE
        if (
            ver.get("verifier_1_label") == "BENIGN_NAMESAKE"
            and lbl == "BENIGN_NAMESAKE"
        ):
            ver["verified_at"] = datetime.now(UTC).isoformat()
        else:
            ver["verified_at"] = None
    else:
        # Already has two verifiers
        pass

    return record


def is_record_double_verified(record: dict[str, Any]) -> bool:
    """Return True only if two distinct verifiers agreed on BENIGN_NAMESAKE."""
    ver = record.get("verification", {})
    v1 = ver.get("verifier_1")
    v2 = ver.get("verifier_2")

    if not v1 or not v2 or v1 == v2:
        return False

    l1 = ver.get("verifier_1_label")
    l2 = ver.get("verifier_2_label")

    if l1 != "BENIGN_NAMESAKE" or l2 != "BENIGN_NAMESAKE":
        return False

    return ver.get("verified_at") is not None


def export_verified_records(
    candidates_path: Path = CANDIDATES_FILE,
    verified_path: Path = VERIFIED_FILE,
) -> list[dict[str, Any]]:
    """Filter candidates.jsonl and export only double-verified records to verified.jsonl."""
    if not candidates_path.exists():
        return []

    verified_records: list[dict[str, Any]] = []

    with open(candidates_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                rec = json.loads(line_str)
                if is_record_double_verified(rec):
                    verified_records.append(rec)
            except json.JSONDecodeError:
                continue

    verified_path.parent.mkdir(parents=True, exist_ok=True)
    with open(verified_path, "w", encoding="utf-8") as f:
        for rec in verified_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    logger.info(
        "Exported %d double-verified records to %s.",
        len(verified_records),
        verified_path,
    )
    return verified_records


def run_interactive_cli(candidates_path: Path = CANDIDATES_FILE) -> None:
    """CLI to inspect and label candidates one by one."""
    if not candidates_path.exists():
        print(f"Candidates file not found: {candidates_path}")
        return

    with open(candidates_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    records = [json.loads(l) for l in lines]
    verifier_name = input("Enter your verifier name: ").strip()
    if not verifier_name:
        print("Verifier name required.")
        return

    updated_count = 0
    for rec in records:
        ver = rec.get("verification", {})
        if (
            ver.get("verifier_1") == verifier_name
            or ver.get("verifier_2") == verifier_name
        ):
            continue
        if is_record_double_verified(rec):
            continue

        cand = rec.get("candidate", {})
        print("\n" + "=" * 60)
        print(f"Case Ref: {rec.get('case_ref')} | Source: {rec.get('source_id')}")
        print(f"Name: {cand.get('display_name')}")
        print(
            f"Handle / Bundle: {cand.get('handle') or cand.get('secondary_identifiers')}"
        )
        print(f"URL: {cand.get('url')}")
        print(f"Publisher: {cand.get('publisher_name')}")

        choice = (
            input(
                "Label (1: BENIGN_NAMESAKE, 2: NEEDS_REVIEW, 3: REJECT, s: skip, q: quit): "
            )
            .strip()
            .lower()
        )
        if choice == "q":
            break
        if choice == "s":
            continue

        label_map = {"1": "BENIGN_NAMESAKE", "2": "NEEDS_REVIEW", "3": "REJECT"}
        lbl = label_map.get(choice)
        if not lbl:
            print("Invalid choice, skipping.")
            continue

        notes = input("Notes (optional): ").strip()
        try:
            verify_candidate_record(rec, verifier_name, lbl, notes)
            updated_count += 1
        except (ValueError, TypeError) as err:
            print(f"Error: {err}")

    if updated_count > 0:
        with open(candidates_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        export_verified_records(candidates_path, VERIFIED_FILE)
        print(f"Saved {updated_count} reviews.")


if __name__ == "__main__":
    run_interactive_cli()
