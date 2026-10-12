"""Recorded Fixture source adapter replaying real captured responses offline.

Owner: Person 3 (backend/app/services/sources/fixtures_recorded.py)
Reference: Contract Sections 5.3, 11.1, 12, Appendix B

Security & Network Rule:
ZERO network calls. Reads local recorded JSON payloads and normalizes them
exclusively through the live adapters' official mapping functions (map_apple_item,
map_bluesky_profile) as SourceMode.CACHED.
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

from .apple import map_apple_item
from .bluesky import map_bluesky_profile

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RECORDED_DIR = REPO_ROOT / "backend" / "tests" / "fixtures" / "recorded"


class RecordedFixtureAdapter:
    """Offline adapter replaying real captured provider responses as CACHED."""

    source_id: str = "recorded_fixtures"
    is_demo_only: bool = True

    def __init__(self, recorded_dir: Path | None = None) -> None:
        self.recorded_dir = recorded_dir or DEFAULT_RECORDED_DIR

    def _load_all_records(self) -> list[NormalizedCandidate]:
        """Load and re-normalize real captured responses through official mappers."""
        candidates: list[NormalizedCandidate] = []

        json_files: list[Path] = []
        if self.recorded_dir.is_dir():
            json_files = sorted(self.recorded_dir.glob("*.json"))
        elif self.recorded_dir.is_file():
            json_files = [self.recorded_dir]

        # Fallback to fixtures root if recorded/ directory is missing or empty
        if not json_files:
            fixtures_root = self.recorded_dir.parent
            for fallback_name in [
                "apple_search_bank_sample.json",
                "bsky_search_actors_bank.json",
            ]:
                fb_path = fixtures_root / fallback_name
                if fb_path.exists():
                    json_files.append(fb_path)

        for file_path in json_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                data = json.loads(content)
            except Exception as err:
                raise ValueError(
                    f"Failed to read JSON from recorded fixture {file_path.name}: {err}"
                ) from err

            if not isinstance(data, dict):
                raise TypeError(
                    f"Invalid recorded fixture root in {file_path.name}: expected object"
                )

            # Original captured timestamp: top-level metadata or file mtime
            captured_raw = data.get("captured_at") or data.get("retrieved_at")
            if captured_raw:
                try:
                    default_retrieved_at = datetime.fromisoformat(str(captured_raw))
                except ValueError:
                    default_retrieved_at = datetime.fromtimestamp(
                        file_path.stat().st_mtime, tz=UTC
                    )
            else:
                default_retrieved_at = datetime.fromtimestamp(
                    file_path.stat().st_mtime, tz=UTC
                )

            # Envelope with pre-normalized candidate records
            if "records" in data and isinstance(data["records"], list):
                for idx, item in enumerate(data["records"]):
                    if not isinstance(item, dict) or "candidate" not in item:
                        raise ValueError(
                            f"Invalid record at {file_path.name}:{idx}: missing 'candidate' object"
                        )
                    cand_dict = dict(item["candidate"])
                    cand_dict["source_mode"] = SourceMode.CACHED

                    # Preserve original timestamp if provided on candidate or item
                    record_time = item.get("captured_at") or cand_dict.get(
                        "retrieved_at"
                    )
                    if record_time:
                        try:
                            if isinstance(record_time, str):
                                cand_dict["retrieved_at"] = datetime.fromisoformat(
                                    record_time
                                )
                            else:
                                cand_dict["retrieved_at"] = record_time
                        except ValueError:
                            cand_dict["retrieved_at"] = default_retrieved_at
                    else:
                        cand_dict["retrieved_at"] = default_retrieved_at

                    try:
                        candidates.append(NormalizedCandidate(**cand_dict))
                    except Exception as err:
                        raise ValueError(
                            f"Invalid record at {file_path.name}:{idx}: {err}"
                        ) from err

            # Apple response shape: {"resultCount": N, "results": [...]}
            elif "results" in data and isinstance(data["results"], list):
                for idx, item in enumerate(data["results"]):
                    if not isinstance(item, dict):
                        raise TypeError(
                            f"Invalid item at {file_path.name}:{idx}: expected object"
                        )
                    if item.get("trackId") and item.get("trackName"):
                        c = map_apple_item(
                            item,
                            source_mode=SourceMode.CACHED,
                            retrieved_at=default_retrieved_at,
                            matched_query=data.get("term", "bank"),
                        )
                        candidates.append(c)

            # Bluesky response shape: {"profiles": [...]} or {"actors": [...]}
            elif ("profiles" in data and isinstance(data["profiles"], list)) or (
                "actors" in data and isinstance(data["actors"], list)
            ):
                profiles_list = data.get("profiles") or data.get("actors")
                for idx, profile in enumerate(profiles_list):
                    if not isinstance(profile, dict):
                        raise TypeError(
                            f"Invalid profile at {file_path.name}:{idx}: expected object"
                        )
                    if profile.get("did"):
                        c = map_bluesky_profile(
                            profile,
                            source_mode=SourceMode.CACHED,
                            retrieved_at=default_retrieved_at,
                            matched_query=data.get("term", "bank"),
                        )
                        candidates.append(c)
            else:
                raise ValueError(
                    f"Recorded fixture {file_path.name} contains unrecognized format: "
                    "expected 'records', 'results', 'profiles', or 'actors'"
                )

        if not candidates:
            raise ValueError(
                f"No valid recorded candidates found in {self.recorded_dir}"
            )

        return candidates

    async def health_check(self) -> SourceHealth:
        """Report static healthy status for offline recorded fixtures."""
        return SourceHealth(
            source_id=self.source_id,
            display_name="Recorded Real Fixtures",
            platform="multi",
            asset_types=[AssetType.IOS_APP, AssetType.SOCIAL_ACCOUNT],
            status=SourceStatus.CONNECTED,
            supported_modes=[SourceMode.CACHED],
            default_mode=SourceMode.CACHED,
            last_checked_at=datetime.now(UTC),
            rate_limit_note="No rate limit (local recorded files)",
            message="Recorded real provider responses served offline as CACHED.",
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
        """Return recorded real candidates normalized as CACHED."""
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

        return SourceResult(
            source_id=self.source_id,
            status=SourceStatus.CONNECTED,
            source_mode=SourceMode.CACHED,
            retrieved_at=now_utc,
            candidates=candidates,
            queries_executed=len(plan.queries) if plan and plan.queries else 1,
            cache_hit_count=len(candidates),
            error_code=None,
            message=f"Loaded {len(candidates)} recorded real fixture records offline as CACHED.",
            duration_ms=2,
        )

    async def lookup(self, identifier: str) -> NormalizedCandidate | None:
        """Lookup by stable identifier in recorded real candidates."""
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


__all__ = ["RecordedFixtureAdapter"]
