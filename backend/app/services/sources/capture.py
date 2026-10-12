"""Real negative candidate capture script.

Owner: Person 3 (backend/app/services/sources/capture.py)
Reference: Contract Section 5.6, 12, 14, Appendix B

Runnable via:
`python -m app.services.sources.capture` from `backend/`

Uses the real Apple and Bluesky adapters (with rate limiting and caching)
to discover and record benign namesake candidates for the evaluation brand.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

# Ensure schemas are bootstrapped before importing sources package
try:
    import app.schemas
except ImportError:
    repo_root = Path(__file__).resolve().parents[4]
    backend_dir = repo_root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    import app.services.sources.tests.conftest  # type: ignore # noqa: F401

from app.schemas import PlannedQuery, QueryPlan
from app.services.sources.apple import AppleItunesAdapter
from app.services.sources.bluesky import BlueskyPublicAdapter

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("threatlens.capture")

REPO_ROOT = Path(__file__).resolve().parents[4]
REAL_NEGATIVES_DIR = REPO_ROOT / "backend" / "tests" / "fixtures" / "real_negatives"
CANDIDATES_FILE = REAL_NEGATIVES_DIR / "candidates.jsonl"

# Fixed namesake-style terms for evaluation brand "kaveri" (distinctive token, separators, variants)
NAMESAKE_TERMS = [
    # Core token & banking/finance terms
    "kaveri",
    "kaveri bank",
    "kaveri mobile",
    "kaveri app",
    "kaveri online",
    "kaveri pay",
    "kaveri finance",
    "kaveri credit",
    # Unrelated commercial & civic entities sharing namesake token
    "kaveri silks",
    "kaveri express",
    "kaveri hospital",
    "kaveri travel",
    "kaveri foods",
    "kaveri news",
    "kaveri jewelry",
    "kaveri foundation",
    "kaveri water",
    # Phonetic and regional spelling variants
    "cauvery",
    "cauvery bank",
    "cauvery silks",
    "cauvery express",
    "cauvery hospital",
]


def load_existing_candidates(
    path: Path,
) -> tuple[dict[tuple[str, str], dict[str, Any]], int]:
    """Load existing candidates keyed by (source_id, stable_identifier)."""
    mapping: dict[tuple[str, str], dict[str, Any]] = {}
    max_idx = 0

    if not path.exists():
        return mapping, max_idx

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
                source_id = record.get("source_id")
                cand = record.get("candidate", {})
                stable_id = cand.get("stable_identifier")
                if source_id and stable_id:
                    mapping[(source_id, stable_id)] = record

                case_ref = record.get("case_ref", "")
                if case_ref.startswith("rn-"):
                    try:
                        idx_num = int(case_ref.split("-")[1])
                        max_idx = max(max_idx, idx_num)
                    except (ValueError, IndexError):
                        pass
            except json.JSONDecodeError:
                continue

    return mapping, max_idx


async def capture_candidates(
    output_file: Path = CANDIDATES_FILE,
    terms: list[str] | None = None,
    apple_adapter: AppleItunesAdapter | None = None,
    bluesky_adapter: BlueskyPublicAdapter | None = None,
) -> list[dict[str, Any]]:
    """Capture real candidates across Apple and Bluesky into candidates.jsonl."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    existing_map, max_idx = load_existing_candidates(output_file)

    active_terms = terms or NAMESAKE_TERMS
    logger.info(
        "Starting candidate capture across %d namesake terms...", len(active_terms)
    )

    apple = apple_adapter or AppleItunesAdapter()
    bsky = bluesky_adapter or BlueskyPublicAdapter()

    planned_queries = [
        PlannedQuery(term=t, kind="NAMESAKE", priority=i + 1)
        for i, t in enumerate(active_terms)
    ]
    plan = QueryPlan(brand_id=uuid4(), queries=planned_queries)

    # 1. Search Apple App Store
    apple_candidates = []
    try:
        logger.info("Querying Apple App Store adapter...")
        apple_res = await apple.search(plan, limit=50)
        apple_candidates = apple_res.candidates
        logger.info(
            "Apple App Store returned %d candidate records.", len(apple_candidates)
        )
    except Exception as err:  # noqa: BLE001
        logger.warning(
            "Apple adapter query failed (recording in log, no backfill): %s", err
        )

    # 2. Search Bluesky
    bluesky_candidates = []
    try:
        logger.info("Querying Bluesky Public AppView adapter...")
        bsky_res = await bsky.search(plan, limit=50)
        bluesky_candidates = bsky_res.candidates
        logger.info("Bluesky returned %d candidate records.", len(bluesky_candidates))
    except Exception as err:  # noqa: BLE001
        logger.warning(
            "Bluesky adapter query failed (recording in log, no backfill): %s", err
        )

    # 3. Merge and deduplicate
    counter = max_idx
    all_incoming = apple_candidates + bluesky_candidates

    for cand in all_incoming:
        key = (cand.source_id, cand.stable_identifier)
        if key in existing_map:
            # Preserve existing case_ref and verification history
            continue

        counter += 1
        case_ref = f"rn-{counter:04d}"
        cand_dict = cand.model_dump(mode="json")

        rec = {
            "case_ref": case_ref,
            "provenance": "REAL_CAPTURED",
            "captured_at": cand.retrieved_at.isoformat()
            if cand.retrieved_at
            else datetime.now(UTC).isoformat(),
            "source_id": cand.source_id,
            "candidate": cand_dict,
            "proposed_label": "BENIGN_NAMESAKE",
            "verification": {
                "verifier_1": None,
                "verifier_2": None,
                "verified_at": None,
                "notes": "",
            },
        }
        existing_map[key] = rec

    # 4. Write output JSONL
    sorted_records = sorted(existing_map.values(), key=lambda r: r.get("case_ref", ""))
    with open(output_file, "w", encoding="utf-8") as f:  # noqa: ASYNC230
        for rec in sorted_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    logger.info(
        "Saved %d total unique candidates to %s.", len(sorted_records), output_file
    )
    return sorted_records


async def main() -> None:
    records = await capture_candidates()
    print(f"Captured {len(records)} candidates successfully.")


if __name__ == "__main__":
    asyncio.run(main())
