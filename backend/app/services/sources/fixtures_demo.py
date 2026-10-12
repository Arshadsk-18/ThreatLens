"""DEMO Fixture source adapter reading local simulated datasets.

Owner: Person 3 (backend/app/services/sources/fixtures_demo.py)
Reference: Contract Sections 5.3, 11.1, 12, Appendix B

Security & Network Rule:
ZERO network calls. Pure local JSON loader. Any record claiming LIVE mode
is strictly rejected. All records are validated against NormalizedCandidate.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from app.schemas import (
    AssetType,
    NormalizedCandidate,
    QueryPlan,
    SourceHealth,
    SourceMode,
    SourceResult,
    SourceStatus,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DEMO_DIR = REPO_ROOT / "backend" / "tests" / "fixtures" / "demo"


class DemoFixtureAdapter:
    """Offline adapter providing simulated candidates for DEMO scans."""

    source_id: str = "demo_fixtures"
    is_demo_only: bool = True

    def __init__(self, demo_dir: Path | None = None) -> None:
        self.demo_dir = demo_dir or DEFAULT_DEMO_DIR

    def _load_all_records(self) -> list[NormalizedCandidate]:
        """Load and validate all records from demo JSON files.

        Enforces that candidate.source_mode is SIMULATED and raises ValueError
        reporting the filename and index on any invalid or LIVE record.
        """
        candidates: list[NormalizedCandidate] = []
        now_utc = datetime.now(UTC)

        json_files: list[Path] = []
        if self.demo_dir.is_dir():
            json_files = sorted(self.demo_dir.glob("*.json"))
        elif self.demo_dir.is_file():
            json_files = [self.demo_dir]

        # Fallback to demo_candidates.json in fixtures root if directory is empty
        if not json_files:
            fallback = self.demo_dir.parent / "demo_candidates.json"
            if fallback.exists():
                json_files = [fallback]

        for file_path in json_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                data = json.loads(content)
            except Exception as err:
                raise ValueError(
                    f"Failed to read JSON from {file_path.name}: {err}"
                ) from err

            if not isinstance(data, dict):
                raise TypeError(
                    f"Invalid JSON root in {file_path.name}: expected object"
                )

            records = data.get("records")
            version = data.get("fixture_version")
            candidates_raw = data.get("candidates")

            # If standard {"fixture_version": 1, "records": [...]} format
            if isinstance(records, list):
                if version is not None and version != 1:
                    raise ValueError(
                        f"Unsupported fixture_version {version} in {file_path.name}: expected version 1"
                    )
                for idx, record in enumerate(records):
                    if not isinstance(record, dict) or "candidate" not in record:
                        raise ValueError(
                            f"Invalid record at {file_path.name}:{idx}: missing 'candidate' object"
                        )

                    cand_raw = dict(record["candidate"])

                    # Rejection rule: record claiming LIVE or CACHED mode is an error
                    mode_val = cand_raw.get("source_mode")
                    if mode_val == "LIVE" or mode_val == SourceMode.LIVE:
                        raise ValueError(
                            f"Invalid record at {file_path.name}:{idx}: "
                            "DEMO fixture candidate claims LIVE mode; must be SIMULATED."
                        )
                    if mode_val == "CACHED" or mode_val == SourceMode.CACHED:
                        raise ValueError(
                            f"Invalid record at {file_path.name}:{idx}: "
                            "DEMO fixture candidate claims CACHED mode; must be SIMULATED."
                        )
                    if mode_val != "SIMULATED" and mode_val != SourceMode.SIMULATED:
                        raise ValueError(
                            f"Invalid record at {file_path.name}:{idx}: "
                            f"DEMO fixture candidate declares source_mode='{mode_val}'; must be SIMULATED."
                        )

                    # Ensure SIMULATED mode and timestamp
                    cand_raw["source_mode"] = SourceMode.SIMULATED
                    if not cand_raw.get("retrieved_at"):
                        cand_raw["retrieved_at"] = now_utc

                    try:
                        candidate = NormalizedCandidate(**cand_raw)
                        candidates.append(candidate)
                    except Exception as err:
                        raise ValueError(
                            f"Invalid record at {file_path.name}:{idx}: {err}"
                        ) from err

            # Backward compatibility with flat {"candidates": [...]}
            elif isinstance(candidates_raw, list):
                for idx, cand_item in enumerate(candidates_raw):
                    cand_raw = dict(cand_item)
                    mode_val = cand_raw.get("source_mode")
                    if mode_val == "LIVE" or mode_val == SourceMode.LIVE:
                        raise ValueError(
                            f"Invalid record at {file_path.name}:{idx}: "
                            "DEMO fixture candidate claims LIVE mode; must be SIMULATED."
                        )
                    if mode_val == "CACHED" or mode_val == SourceMode.CACHED:
                        raise ValueError(
                            f"Invalid record at {file_path.name}:{idx}: "
                            "DEMO fixture candidate claims CACHED mode; must be SIMULATED."
                        )
                    cand_raw["source_mode"] = SourceMode.SIMULATED
                    if not cand_raw.get("retrieved_at"):
                        cand_raw["retrieved_at"] = now_utc
                    try:
                        candidate = NormalizedCandidate(**cand_raw)
                        candidates.append(candidate)
                    except Exception as err:
                        raise ValueError(
                            f"Invalid record at {file_path.name}:{idx}: {err}"
                        ) from err
            else:
                raise TypeError(
                    f"Fixture {file_path.name} contains unrecognized format: expected 'records' or 'candidates' list"
                )

        if not candidates:
            raise ValueError(f"No valid demo candidates found in {self.demo_dir}")

        return candidates

    async def health_check(self) -> SourceHealth:
        """Report static healthy status for offline demo fixtures."""
        return SourceHealth(
            source_id=self.source_id,
            display_name="Demo Fixtures (Simulated)",
            platform="demo",
            asset_types=[
                AssetType.IOS_APP,
                AssetType.ANDROID_APP,
                AssetType.SOCIAL_ACCOUNT,
            ],
            status=SourceStatus.CONNECTED,
            supported_modes=[SourceMode.SIMULATED],
            default_mode=SourceMode.SIMULATED,
            last_checked_at=datetime.now(UTC),
            rate_limit_note="No rate limit (local fixtures)",
            message="Offline simulated fixtures available for DEMO scans.",
        )

    async def search(
        self,
        plan: QueryPlan,
        limit: int = 50,
        *,
        force_refresh: bool = False,
        allow_stale_cache: bool = False,
        is_live_scan: bool = False,
        **kwargs: object,
    ) -> SourceResult:
        """Return all simulated demo records (brand-agnostic funnel)."""
        if (
            is_live_scan
            or kwargs.get("mode") == "LIVE"
            or kwargs.get("scan_mode") == "LIVE"
        ):
            raise ValueError(
                f"Source '{self.source_id}' is demo-only and cannot be used in a LIVE scan (MODE_NOT_ALLOWED)."
            )

        now_utc = datetime.now(UTC)
        candidates = self._load_all_records()

        # In DEMO mode, return all records (the scoring funnel filters them)
        return SourceResult(
            source_id=self.source_id,
            status=SourceStatus.CONNECTED,
            source_mode=SourceMode.SIMULATED,
            retrieved_at=now_utc,
            candidates=candidates,
            queries_executed=len(plan.queries) if plan and plan.queries else 1,
            cache_hit_count=0,
            error_code=None,
            message=f"Served {len(candidates)} simulated demo records offline.",
            duration_ms=1,
        )

    async def lookup(self, identifier: str) -> NormalizedCandidate | None:
        """Lookup by stable identifier or secondary identifier in demo records."""
        target = identifier.strip()
        candidates = self._load_all_records()
        for cand in candidates:
            if cand.stable_identifier == target:
                return cand
            if target in cand.secondary_identifiers.values():
                return cand
            if cand.handle and cand.handle == target:
                return cand
        return None


__all__ = ["DemoFixtureAdapter"]
