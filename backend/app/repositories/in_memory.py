"""In-memory implementations of all repository protocols for ThreatLens."""

from __future__ import annotations

import copy
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from .protocols import (
    AssessmentRepo,
    AssetRepo,
    AuditEventRecord,
    AuditRepo,
    BrandRepo,
    CachedResponse,
    CacheRepo,
    CandidateRepo,
    ClearedRecord,
    DecisionRepo,
    DomainValidationError,
    EntityNotFoundError,
    FindingRecord,
    Page,
    ScanRepo,
    compute_content_hash,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _gen_id() -> str:
    import uuid

    return str(uuid.uuid4())


class InMemoryAuditRepo(AuditRepo):
    """In-memory implementation of AuditRepo."""

    def __init__(self) -> None:
        self.events: list[AuditEventRecord] = []

    def log(
        self,
        brand_id: str,
        actor_label: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any],
    ) -> AuditEventRecord:
        record = AuditEventRecord(
            id=_gen_id(),
            brand_id=brand_id,
            actor_label=actor_label,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            details=copy.deepcopy(details),
            created_at=_utc_now(),
        )
        self.events.append(record)
        return record

    def list(
        self, brand_id: str, limit: int = 20, offset: int = 0
    ) -> Page[AuditEventRecord]:
        filtered = [e for e in self.events if e.brand_id == brand_id]
        filtered.sort(key=lambda e: e.created_at, reverse=True)
        total = len(filtered)
        items = filtered[offset : offset + limit]
        return Page(items=items, total=total, limit=limit, offset=offset)


class InMemoryBrandRepo(BrandRepo):
    """In-memory implementation of BrandRepo."""

    def __init__(self) -> None:
        self.brands: dict[str, dict[str, Any]] = {}

    def create(self, brand_data: dict[str, Any]) -> dict[str, Any]:
        brand_id = brand_data.get("id") or _gen_id()
        now = _utc_now()
        data = copy.deepcopy(brand_data)
        data["id"] = brand_id
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        self.brands[brand_id] = data
        return copy.deepcopy(data)

    def get(self, brand_id: str) -> dict[str, Any] | None:
        data = self.brands.get(brand_id)
        return copy.deepcopy(data) if data else None

    def list(self, limit: int = 20, offset: int = 0) -> Page[dict[str, Any]]:
        all_brands = sorted(
            self.brands.values(), key=lambda b: b.get("created_at", _utc_now())
        )
        total = len(all_brands)
        items = [copy.deepcopy(b) for b in all_brands[offset : offset + limit]]
        return Page(items=items, total=total, limit=limit, offset=offset)

    def update(
        self, brand_id: str, update_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        if brand_id not in self.brands:
            return None
        brand = self.brands[brand_id]
        for k, v in update_data.items():
            if k != "id":
                brand[k] = copy.deepcopy(v)
        brand["updated_at"] = _utc_now()
        return copy.deepcopy(brand)


class InMemoryAssetRepo(AssetRepo):
    """In-memory implementation of AssetRepo."""

    def __init__(self, audit_repo: AuditRepo | None = None) -> None:
        self.assets: dict[str, dict[str, Any]] = {}
        self.audit_repo = audit_repo

    def create(
        self, asset_data: dict[str, Any], actor_label: str = "system"
    ) -> dict[str, Any]:
        brand_id = asset_data["brand_id"]
        platform = asset_data["platform"]
        stable_id = asset_data["stable_identifier"]

        # Check unique constraint (brand_id, platform, stable_identifier)
        for existing in self.assets.values():
            if (
                existing["brand_id"] == brand_id
                and existing["platform"] == platform
                and existing["stable_identifier"] == stable_id
            ):
                raise DomainValidationError(
                    f"Asset already exists with platform {platform} and identifier {stable_id}"
                )

        asset_id = asset_data.get("id") or _gen_id()
        now = _utc_now()
        data = copy.deepcopy(asset_data)
        data["id"] = asset_id
        data.setdefault("is_verified", False)
        data.setdefault("trust_publisher", False)
        data.setdefault("is_active", True)
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        self.assets[asset_id] = data

        if self.audit_repo:
            self.audit_repo.log(
                brand_id=brand_id,
                actor_label=actor_label,
                event_type="OFFICIAL_ASSET_CREATED",
                entity_type="official_assets",
                entity_id=asset_id,
                details={
                    "display_name": data.get("display_name"),
                    "platform": platform,
                },
            )

        return copy.deepcopy(data)

    def get(self, asset_id: str) -> dict[str, Any] | None:
        data = self.assets.get(asset_id)
        return copy.deepcopy(data) if data else None

    def list_by_brand(
        self,
        brand_id: str,
        asset_type: str | None = None,
        relationship: str | None = None,
        is_verified: bool | None = None,
        is_active: bool | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        for asset in self.assets.values():
            if asset["brand_id"] != brand_id:
                continue
            if asset_type is not None and asset.get("asset_type") != asset_type:
                continue
            if relationship is not None and asset.get("relationship") != relationship:
                continue
            if is_verified is not None and asset.get("is_verified") != is_verified:
                continue
            if is_active is not None and asset.get("is_active") != is_active:
                continue
            results.append(copy.deepcopy(asset))
        return results

    def update(
        self, asset_id: str, update_data: dict[str, Any], actor_label: str = "system"
    ) -> dict[str, Any] | None:
        if asset_id not in self.assets:
            return None
        asset = self.assets[asset_id]
        for k, v in update_data.items():
            if k not in ("id", "brand_id"):
                asset[k] = copy.deepcopy(v)
        asset["updated_at"] = _utc_now()

        if self.audit_repo:
            self.audit_repo.log(
                brand_id=asset["brand_id"],
                actor_label=actor_label,
                event_type="OFFICIAL_ASSET_UPDATED",
                entity_type="official_assets",
                entity_id=asset_id,
                details=update_data,
            )

        return copy.deepcopy(asset)


class InMemoryScanRepo(ScanRepo):
    """In-memory implementation of ScanRepo."""

    def __init__(self) -> None:
        self.scans: dict[str, dict[str, Any]] = {}

    def create(self, scan_data: dict[str, Any]) -> dict[str, Any]:
        scan_id = scan_data.get("id") or _gen_id()
        now = _utc_now()
        data = copy.deepcopy(scan_data)
        data["id"] = scan_id
        data.setdefault("status", "QUEUED")
        data.setdefault("stage", "queued")
        data.setdefault("progress_percent", 0)
        data.setdefault("options", {})
        data.setdefault("source_outcomes", [])
        data.setdefault("funnel", {})
        data.setdefault("findings_by_severity", {})
        data.setdefault("events", [])
        data.setdefault("created_at", now)
        self.scans[scan_id] = data
        return copy.deepcopy(data)

    def get(self, scan_id: str) -> dict[str, Any] | None:
        data = self.scans.get(scan_id)
        return copy.deepcopy(data) if data else None

    def list(
        self, brand_id: str, limit: int = 20, offset: int = 0
    ) -> Page[dict[str, Any]]:
        filtered = [s for s in self.scans.values() if s.get("brand_id") == brand_id]
        filtered.sort(key=lambda s: s.get("created_at", _utc_now()), reverse=True)
        total = len(filtered)
        items = [copy.deepcopy(s) for s in filtered[offset : offset + limit]]
        return Page(items=items, total=total, limit=limit, offset=offset)

    def update_progress(
        self, scan_id: str, stage: str, progress_percent: int
    ) -> dict[str, Any] | None:
        scan = self.scans.get(scan_id)
        if not scan:
            return None
        scan["stage"] = stage
        scan["progress_percent"] = progress_percent
        if scan.get("started_at") is None and stage != "queued":
            scan["started_at"] = _utc_now()
        return copy.deepcopy(scan)

    def append_event(self, scan_id: str, event_data: dict[str, Any]) -> None:
        scan = self.scans.get(scan_id)
        if not scan:
            return
        events = scan.setdefault("events", [])
        events.append(copy.deepcopy(event_data))
        # Capped at 200 events
        if len(events) > 200:
            scan["events"] = events[-200:]

    def finish(
        self,
        scan_id: str,
        status: str,
        source_outcomes: list[Any],
        funnel: dict[str, Any],
        findings_by_severity: dict[str, int],
        error_message: str | None = None,
    ) -> dict[str, Any] | None:
        scan = self.scans.get(scan_id)
        if not scan:
            return None
        scan["status"] = status
        scan["stage"] = "completed" if "COMPLETED" in status else "failed"
        scan["progress_percent"] = 100
        scan["source_outcomes"] = copy.deepcopy(source_outcomes)
        scan["funnel"] = copy.deepcopy(funnel)
        scan["findings_by_severity"] = copy.deepcopy(findings_by_severity)
        scan["error_message"] = error_message
        scan["completed_at"] = _utc_now()
        return copy.deepcopy(scan)


class InMemoryCandidateRepo(CandidateRepo):
    """In-memory implementation of CandidateRepo with decision memory."""

    def __init__(self) -> None:
        self.candidates: dict[str, dict[str, Any]] = {}
        # index by (brand_id, platform, stable_identifier) -> id
        self.by_key: dict[tuple[str, str, str], str] = {}

    def _extract(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def upsert(self, candidate: Any, brand_id: str, scan_id: str) -> dict[str, Any]:
        platform = self._extract(candidate, "platform")
        stable_id = str(self._extract(candidate, "stable_identifier"))
        display_name = self._extract(candidate, "display_name") or ""
        publisher_name = self._extract(candidate, "publisher_name")
        description = self._extract(candidate, "description")
        icon_hash = self._extract(candidate, "icon_hash")

        content_hash = compute_content_hash(
            display_name=display_name,
            publisher_name=publisher_name,
            description=description,
            icon_hash=icon_hash,
        )

        now = _utc_now()
        retrieved_at = self._extract(candidate, "retrieved_at", now)
        key = (str(brand_id), str(platform), stable_id)

        if key in self.by_key:
            cand_id = self.by_key[key]
            existing = self.candidates[cand_id]
            # Update observed fields, last_seen_at, last_scan_id, content_hash
            existing["display_name"] = display_name
            existing["handle"] = self._extract(candidate, "handle")
            existing["publisher_name"] = publisher_name
            existing["developer_id"] = self._extract(candidate, "developer_id")
            existing["description"] = description
            existing["category"] = self._extract(candidate, "category")
            existing["external_links"] = copy.deepcopy(
                self._extract(candidate, "external_links", [])
            )
            existing["icon_url"] = self._extract(candidate, "icon_url")
            existing["icon_hash"] = icon_hash
            existing["canonical_url"] = self._extract(candidate, "canonical_url")
            existing["created_at_source"] = self._extract(
                candidate, "created_at_source"
            )
            existing["followers"] = self._extract(candidate, "followers")
            existing["following"] = self._extract(candidate, "following")
            existing["posts_count"] = self._extract(candidate, "posts_count")
            existing["rating_count"] = self._extract(candidate, "rating_count")
            existing["last_source_mode"] = str(
                self._extract(candidate, "source_mode", "LIVE")
            )
            existing["secondary_identifiers"] = copy.deepcopy(
                self._extract(candidate, "secondary_identifiers", {})
            )
            existing["content_hash"] = content_hash
            existing["last_seen_at"] = retrieved_at or now
            existing["last_scan_id"] = str(scan_id)
            # Preserves first_seen_at, analyst_status, and analyst_reason (decision memory)
            return copy.deepcopy(existing)

        # Insert new candidate
        cand_id = _gen_id()
        data = {
            "id": cand_id,
            "brand_id": str(brand_id),
            "platform": str(platform),
            "asset_type": str(self._extract(candidate, "asset_type", "IOS_APP")),
            "stable_identifier": stable_id,
            "secondary_identifiers": copy.deepcopy(
                self._extract(candidate, "secondary_identifiers", {})
            ),
            "display_name": display_name,
            "handle": self._extract(candidate, "handle"),
            "publisher_name": publisher_name,
            "developer_id": self._extract(candidate, "developer_id"),
            "description": description,
            "category": self._extract(candidate, "category"),
            "external_links": copy.deepcopy(
                self._extract(candidate, "external_links", [])
            ),
            "icon_url": self._extract(candidate, "icon_url"),
            "icon_hash": icon_hash,
            "canonical_url": self._extract(candidate, "canonical_url"),
            "created_at_source": self._extract(candidate, "created_at_source"),
            "followers": self._extract(candidate, "followers"),
            "following": self._extract(candidate, "following"),
            "posts_count": self._extract(candidate, "posts_count"),
            "rating_count": self._extract(candidate, "rating_count"),
            "last_source_mode": str(self._extract(candidate, "source_mode", "LIVE")),
            "content_hash": content_hash,
            "analyst_status": "NEW",
            "analyst_reason": None,
            "first_seen_at": retrieved_at or now,
            "last_seen_at": retrieved_at or now,
            "last_scan_id": str(scan_id),
        }
        self.candidates[cand_id] = data
        self.by_key[key] = cand_id
        return copy.deepcopy(data)

    def get(self, candidate_id: str) -> dict[str, Any] | None:
        data = self.candidates.get(candidate_id)
        return copy.deepcopy(data) if data else None

    def get_by_stable_id(
        self, brand_id: str, platform: str, stable_identifier: str
    ) -> dict[str, Any] | None:
        key = (str(brand_id), str(platform), str(stable_identifier))
        cand_id = self.by_key.get(key)
        return self.get(cand_id) if cand_id else None


class InMemoryDecisionRepo(DecisionRepo):
    """In-memory implementation of DecisionRepo with atomic validation and audit logging."""

    def __init__(
        self,
        candidate_repo: InMemoryCandidateRepo,
        audit_repo: AuditRepo | None = None,
    ) -> None:
        self.candidate_repo = candidate_repo
        self.audit_repo = audit_repo
        self.decisions: list[dict[str, Any]] = []
        # candidate_id -> content_hash at decision time
        self.hash_at_decision: dict[str, str] = {}

    def record(
        self,
        candidate_id: str,
        assessment_id: str | None,
        new_status: str,
        decision_reason: str,
        notes: str | None = None,
        actor_label: str = "analyst",
    ) -> dict[str, Any]:
        # Validate decision_reason is required for DISMISSED_FALSE_POSITIVE and CONFIRMED_SUSPICIOUS
        if new_status in ("DISMISSED_FALSE_POSITIVE", "CONFIRMED_SUSPICIOUS") and (
            not decision_reason or not decision_reason.strip()
        ):
            raise DomainValidationError(
                f"decision_reason is required for status '{new_status}'"
            )

        candidate = self.candidate_repo.candidates.get(candidate_id)
        if not candidate:
            raise EntityNotFoundError(f"Candidate {candidate_id} not found")

        previous_status = candidate["analyst_status"]
        candidate["analyst_status"] = new_status
        candidate["analyst_reason"] = decision_reason

        # Record content hash at decision time
        self.hash_at_decision[candidate_id] = candidate.get("content_hash", "")

        dec_id = _gen_id()
        decision_row = {
            "id": dec_id,
            "candidate_asset_id": candidate_id,
            "assessment_id": assessment_id,
            "previous_status": previous_status,
            "new_status": new_status,
            "decision_reason": decision_reason,
            "notes": notes,
            "actor_label": actor_label,
            "created_at": _utc_now(),
        }
        self.decisions.append(decision_row)

        if self.audit_repo:
            self.audit_repo.log(
                brand_id=candidate["brand_id"],
                actor_label=actor_label,
                event_type="ANALYST_DECISION",
                entity_type="candidate_assets",
                entity_id=candidate_id,
                details={
                    "previous_status": previous_status,
                    "new_status": new_status,
                    "decision_reason": decision_reason,
                    "assessment_id": assessment_id,
                    "content_hash_at_decision": candidate.get("content_hash"),
                },
            )

        return copy.deepcopy(decision_row)

    def list_by_candidate(self, candidate_id: str) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(d)
            for d in self.decisions
            if d["candidate_asset_id"] == candidate_id
        ]


class InMemoryCacheRepo(CacheRepo):
    """In-memory implementation of CacheRepo with TTL awareness."""

    def __init__(self) -> None:
        self.cache: dict[str, CachedResponse] = {}

    def get(self, key: str, max_age_s: int | None = None) -> CachedResponse | None:
        item = self.cache.get(key)
        if not item:
            return None

        age_s = (_utc_now() - item.retrieved_at).total_seconds()

        # If max_age_s is specified, enforce it along with TTL
        if max_age_s is not None:
            if age_s > max_age_s or age_s > item.ttl_seconds:
                return None
            return copy.deepcopy(item)

        # If max_age_s is None, stale read is explicitly permitted!
        return copy.deepcopy(item)

    def put(
        self,
        key: str,
        source_id: str,
        request: dict[str, Any],
        response: dict[str, Any],
        ttl_seconds: int = 3600,
    ) -> None:
        self.cache[key] = CachedResponse(
            key=key,
            source_id=source_id,
            request=copy.deepcopy(request),
            response=copy.deepcopy(response),
            retrieved_at=_utc_now(),
            ttl_seconds=ttl_seconds,
        )


class InMemoryAssessmentRepo(AssessmentRepo):
    """In-memory implementation of AssessmentRepo."""

    def __init__(
        self,
        candidate_repo: InMemoryCandidateRepo,
        decision_repo: InMemoryDecisionRepo | None = None,
    ) -> None:
        self.candidate_repo = candidate_repo
        self.decision_repo = decision_repo
        self.assessments: dict[str, dict[str, Any]] = {}
        self.evidence: list[dict[str, Any]] = []

    def _extract(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def save(
        self,
        scan_id: str,
        candidate_id: str,
        result: Any,
        evidence: Sequence[Any],
        brand_id: str | None = None,
    ) -> str:
        candidate = self.candidate_repo.get(candidate_id)
        resolved_brand_id = brand_id or (candidate["brand_id"] if candidate else "")
        ass_id = _gen_id()
        now = _utc_now()

        breakdown = self._extract(result, "score_breakdown") or self._extract(
            result, "breakdown", []
        )
        corroborating = self._extract(result, "corroborating_groups", [])
        gates = self._extract(result, "gates_applied", [])

        data = {
            "id": ass_id,
            "scan_id": str(scan_id),
            "brand_id": str(resolved_brand_id),
            "candidate_asset_id": str(candidate_id),
            "identity_decision": str(self._extract(result, "identity_decision")),
            "rule": str(self._extract(result, "rule", "")),
            "matched_official_asset_id": self._extract(
                result, "matched_official_asset_id"
            ),
            "risk_score": self._extract(result, "risk_score"),
            "severity": self._extract(result, "severity"),
            "evidence_coverage": self._extract(result, "evidence_coverage"),
            "corroborating_groups": copy.deepcopy(corroborating),
            "gates_applied": copy.deepcopy(gates),
            "score_breakdown": copy.deepcopy(breakdown),
            "technique": str(self._extract(result, "technique", "NONE")),
            "explanation": str(self._extract(result, "explanation", "")),
            "source_mode": str(self._extract(result, "source_mode", "LIVE")),
            "scoring_version": str(self._extract(result, "scoring_version", "3.0.0")),
            "nearest_official_asset_id": self._extract(
                result, "nearest_official_asset_id"
            ),
            "created_at": now,
        }
        self.assessments[ass_id] = data

        for ev in evidence:
            ev_id = _gen_id()
            ev_data = {
                "id": ev_id,
                "assessment_id": ass_id,
                "candidate_asset_id": str(candidate_id),
                "scan_id": str(scan_id),
                "source_id": str(self._extract(ev, "source_id")),
                "evidence_type": str(self._extract(ev, "evidence_type")),
                "status": str(self._extract(ev, "status", "OBSERVED")),
                "field_name": str(self._extract(ev, "field_name")),
                "observed_value": self._extract(ev, "observed_value"),
                "source_url": self._extract(ev, "source_url"),
                "observed_at": self._extract(ev, "observed_at", now),
                "notes": self._extract(ev, "notes"),
            }
            self.evidence.append(ev_data)

        return ass_id

    def list_findings(
        self,
        brand_id: str | None = None,
        scan_id: str | None = None,
        status: str | None = None,
        asset_type: str | None = None,
        platform: str | None = None,
        severity: str | None = None,
        min_score: int | None = None,
        source_mode: str | None = None,
        q: str | None = None,
        latest_only: bool = True,
        include_dismissed: bool = False,
        sort: str = "score_desc",
        limit: int = 20,
        offset: int = 0,
    ) -> Page[FindingRecord]:
        # Filter only CANDIDATE_FOR_REVIEW
        all_candidates = {c["id"]: c for c in self.candidate_repo.candidates.values()}
        items_by_cand: dict[str, list[dict[str, Any]]] = {}

        for ass in self.assessments.values():
            if ass["identity_decision"] != "CANDIDATE_FOR_REVIEW":
                continue
            if brand_id and ass["brand_id"] != brand_id:
                continue
            if scan_id and ass["scan_id"] != scan_id:
                continue
            if severity and ass["severity"] != severity:
                continue
            if min_score is not None and (
                ass["risk_score"] is None or ass["risk_score"] < min_score
            ):
                continue
            if source_mode and ass["source_mode"] != source_mode:
                continue

            cand = all_candidates.get(ass["candidate_asset_id"])
            if not cand:
                continue
            if status and cand["analyst_status"] != status:
                continue
            if asset_type and cand["asset_type"] != asset_type:
                continue
            if platform and cand["platform"] != platform:
                continue
            if q:
                q_lower = q.lower()
                name_match = q_lower in (cand.get("display_name") or "").lower()
                pub_match = q_lower in (cand.get("publisher_name") or "").lower()
                handle_match = q_lower in (cand.get("handle") or "").lower()
                if not (name_match or pub_match or handle_match):
                    continue

            items_by_cand.setdefault(ass["candidate_asset_id"], []).append(ass)

        # Apply latest_only per candidate
        eligible_assessments: list[dict[str, Any]] = []
        for cand_asses in items_by_cand.values():
            cand_asses.sort(key=lambda a: a["created_at"], reverse=True)
            if latest_only:
                eligible_assessments.append(cand_asses[0])
            else:
                eligible_assessments.extend(cand_asses)

        records: list[FindingRecord] = []
        for ass in eligible_assessments:
            cand = all_candidates[ass["candidate_asset_id"]]
            is_dismissed = cand.get("analyst_status") == "DISMISSED_FALSE_POSITIVE"

            # Check changed_since_decision
            changed_since_decision = False
            if self.decision_repo:
                dec_hash = self.decision_repo.hash_at_decision.get(cand["id"])
                if dec_hash and dec_hash != cand.get("content_hash"):
                    changed_since_decision = True

            # If dismissed: hidden by default unless changed_since_decision
            if is_dismissed and not include_dismissed and not changed_since_decision:
                continue

            cand_summary = {
                "platform": cand.get("platform"),
                "asset_type": cand.get("asset_type"),
                "stable_identifier": cand.get("stable_identifier"),
                "display_name": cand.get("display_name"),
                "handle": cand.get("handle"),
                "publisher_name": cand.get("publisher_name"),
                "icon_url": cand.get("icon_url"),
                "canonical_url": cand.get("canonical_url"),
            }

            top_signals = []
            for item in ass.get("score_breakdown", []):
                if item.get("points", 0) > 0:
                    top_signals.append(
                        {
                            "signal": item.get("signal"),
                            "points": item.get("points"),
                            "max_points": item.get("max_points"),
                            "reason": item.get("reason"),
                        }
                    )
            top_signals = top_signals[:2]

            rec = FindingRecord(
                id=ass["id"],
                brand_id=ass["brand_id"],
                scan_id=ass["scan_id"],
                candidate=cand_summary,
                risk_score=ass.get("risk_score"),
                severity=ass.get("severity"),
                evidence_coverage=ass.get("evidence_coverage"),
                technique=ass.get("technique", "NONE"),
                top_signals=top_signals,
                status=cand.get("analyst_status", "NEW"),
                source_mode=ass.get("source_mode", "LIVE"),
                observed_at=cand.get("last_seen_at"),
                changed_since_decision=changed_since_decision,
                candidate_asset_id=cand["id"],
            )
            records.append(rec)

        # Sorting: score_desc | score_asc | seen_desc | name_asc
        if sort == "score_asc":
            records.sort(key=lambda r: r.risk_score or 0)
        elif sort == "seen_desc":
            records.sort(key=lambda r: r.observed_at or _utc_now(), reverse=True)
        elif sort == "name_asc":
            records.sort(key=lambda r: (r.candidate.get("display_name") or "").lower())
        else:  # score_desc
            records.sort(key=lambda r: r.risk_score or 0, reverse=True)

        total = len(records)
        paginated = records[offset : offset + limit]
        return Page(items=paginated, total=total, limit=limit, offset=offset)

    def list_cleared(
        self,
        brand_id: str | None = None,
        decision: str | None = None,
        scan_id: str | None = None,
        platform: str | None = None,
        q: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Page[ClearedRecord]:
        all_candidates = {c["id"]: c for c in self.candidate_repo.candidates.values()}
        records: list[ClearedRecord] = []

        for ass in self.assessments.values():
            if ass["identity_decision"] == "CANDIDATE_FOR_REVIEW":
                continue
            if brand_id and ass["brand_id"] != brand_id:
                continue
            if decision and ass["identity_decision"] != decision:
                continue
            if scan_id and ass["scan_id"] != scan_id:
                continue

            cand = all_candidates.get(ass["candidate_asset_id"])
            if not cand:
                continue
            if platform and cand["platform"] != platform:
                continue
            if q:
                q_lower = q.lower()
                name_match = q_lower in (cand.get("display_name") or "").lower()
                pub_match = q_lower in (cand.get("publisher_name") or "").lower()
                if not (name_match or pub_match):
                    continue

            cand_summary = {
                "platform": cand.get("platform"),
                "asset_type": cand.get("asset_type"),
                "stable_identifier": cand.get("stable_identifier"),
                "display_name": cand.get("display_name"),
                "publisher_name": cand.get("publisher_name"),
                "icon_url": cand.get("icon_url"),
            }

            rec = ClearedRecord(
                id=ass["id"],
                scan_id=ass["scan_id"],
                candidate=cand_summary,
                decision=ass["identity_decision"],
                rule=ass["rule"],
                matched_official_asset_id=ass.get("matched_official_asset_id"),
                explanation=ass.get("explanation", ""),
                risk_score=ass.get("risk_score"),
                source_mode=ass.get("source_mode", "LIVE"),
                observed_at=cand.get("last_seen_at"),
                candidate_asset_id=cand["id"],
            )
            records.append((ass.get("created_at") or _utc_now(), rec))

        records.sort(key=lambda item: item[0], reverse=True)
        sorted_records = [r for _, r in records]
        total = len(sorted_records)
        paginated = sorted_records[offset : offset + limit]
        return Page(items=paginated, total=total, limit=limit, offset=offset)
