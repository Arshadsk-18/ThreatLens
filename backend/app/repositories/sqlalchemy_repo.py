"""SQLAlchemy implementations of all ThreatLens repository protocols."""

from __future__ import annotations

import copy
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from app.db.base import generate_uuid, utc_now
from app.db.models import (
    AnalystDecision,
    Assessment,
    AuditEvent,
    Brand,
    CandidateAsset,
    Evidence,
    OfficialAsset,
    ResponseCache,
    Scan,
)
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

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


def _extract(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class SqlAlchemyAuditRepo(AuditRepo):
    """SQLAlchemy implementation of AuditRepo."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def log(
        self,
        brand_id: str,
        actor_label: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any],
    ) -> AuditEventRecord:
        with self.session_factory() as session:
            event = AuditEvent(
                id=generate_uuid(),
                brand_id=brand_id,
                actor_label=actor_label,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                details=copy.deepcopy(details),
                created_at=utc_now(),
            )
            session.add(event)
            session.commit()
            return AuditEventRecord(
                id=event.id,
                brand_id=event.brand_id,
                actor_label=event.actor_label,
                event_type=event.event_type,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                details=event.details,
                created_at=event.created_at,
            )

    def list(
        self, brand_id: str, limit: int = 20, offset: int = 0
    ) -> Page[AuditEventRecord]:
        with self.session_factory() as session:
            count_stmt = select(func.count(AuditEvent.id)).where(
                AuditEvent.brand_id == brand_id
            )
            total = session.scalar(count_stmt) or 0

            stmt = (
                select(AuditEvent)
                .where(AuditEvent.brand_id == brand_id)
                .order_by(desc(AuditEvent.created_at))
                .limit(limit)
                .offset(offset)
            )
            rows = session.scalars(stmt).all()
            items = [
                AuditEventRecord(
                    id=r.id,
                    brand_id=r.brand_id,
                    actor_label=r.actor_label,
                    event_type=r.event_type,
                    entity_type=r.entity_type,
                    entity_id=r.entity_id,
                    details=r.details,
                    created_at=r.created_at,
                )
                for r in rows
            ]
            return Page(items=items, total=total, limit=limit, offset=offset)


class SqlAlchemyBrandRepo(BrandRepo):
    """SQLAlchemy implementation of BrandRepo."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def _to_dict(self, brand: Brand) -> dict[str, Any]:
        return {
            "id": brand.id,
            "name": brand.name,
            "description": brand.description,
            "official_domains": brand.official_domains,
            "keywords": brand.keywords,
            "distinctive_tokens": brand.distinctive_tokens,
            "generic_tokens_extra": brand.generic_tokens_extra,
            "industry_category": brand.industry_category,
            "demo_brand": brand.demo_brand,
            "created_at": brand.created_at,
            "updated_at": brand.updated_at,
        }

    def create(self, brand_data: dict[str, Any]) -> dict[str, Any]:
        with self.session_factory() as session:
            brand = Brand(
                id=brand_data.get("id") or generate_uuid(),
                name=brand_data["name"],
                description=brand_data.get("description"),
                official_domains=copy.deepcopy(brand_data.get("official_domains", [])),
                keywords=copy.deepcopy(brand_data.get("keywords", [])),
                distinctive_tokens=copy.deepcopy(
                    brand_data.get("distinctive_tokens", [])
                ),
                generic_tokens_extra=copy.deepcopy(
                    brand_data.get("generic_tokens_extra", [])
                ),
                industry_category=brand_data.get("industry_category"),
                demo_brand=brand_data.get("demo_brand", False),
            )
            session.add(brand)
            session.commit()
            session.refresh(brand)
            return self._to_dict(brand)

    def get(self, brand_id: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            brand = session.get(Brand, brand_id)
            return self._to_dict(brand) if brand else None

    def list(self, limit: int = 20, offset: int = 0) -> Page[dict[str, Any]]:
        with self.session_factory() as session:
            total = session.scalar(select(func.count(Brand.id))) or 0
            stmt = select(Brand).order_by(Brand.created_at).limit(limit).offset(offset)
            brands = session.scalars(stmt).all()
            return Page(
                items=[self._to_dict(b) for b in brands],
                total=total,
                limit=limit,
                offset=offset,
            )

    def update(
        self, brand_id: str, update_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        with self.session_factory() as session:
            brand = session.get(Brand, brand_id)
            if not brand:
                return None
            for k, v in update_data.items():
                if hasattr(brand, k) and k not in ("id", "created_at"):
                    setattr(brand, k, copy.deepcopy(v))
            brand.updated_at = utc_now()
            session.commit()
            session.refresh(brand)
            return self._to_dict(brand)


class SqlAlchemyAssetRepo(AssetRepo):
    """SQLAlchemy implementation of AssetRepo."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        audit_repo: AuditRepo | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.audit_repo = audit_repo

    def _to_dict(self, asset: OfficialAsset) -> dict[str, Any]:
        return {
            "id": asset.id,
            "brand_id": asset.brand_id,
            "asset_type": asset.asset_type,
            "platform": asset.platform,
            "stable_identifier": asset.stable_identifier,
            "secondary_identifiers": asset.secondary_identifiers,
            "developer_id": asset.developer_id,
            "publisher_name": asset.publisher_name,
            "display_name": asset.display_name,
            "handle": asset.handle,
            "description": asset.description,
            "canonical_url": asset.canonical_url,
            "icon_url": asset.icon_url,
            "icon_hash": asset.icon_hash,
            "relationship": asset.relationship,
            "verification_method": asset.verification_method,
            "is_verified": asset.is_verified,
            "trust_publisher": asset.trust_publisher,
            "is_active": asset.is_active,
            "notes": asset.notes,
            "created_at": asset.created_at,
            "updated_at": asset.updated_at,
        }

    def create(
        self, asset_data: dict[str, Any], actor_label: str = "system"
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            brand_id = asset_data["brand_id"]
            platform = asset_data["platform"]
            stable_id = str(asset_data["stable_identifier"])

            # Check uniqueness before insert
            existing = session.scalar(
                select(OfficialAsset).where(
                    OfficialAsset.brand_id == brand_id,
                    OfficialAsset.platform == platform,
                    OfficialAsset.stable_identifier == stable_id,
                )
            )
            if existing:
                raise DomainValidationError(
                    f"Asset already exists for platform {platform} and identifier {stable_id}"
                )

            asset = OfficialAsset(
                id=asset_data.get("id") or generate_uuid(),
                brand_id=brand_id,
                asset_type=asset_data["asset_type"],
                platform=platform,
                stable_identifier=stable_id,
                secondary_identifiers=copy.deepcopy(
                    asset_data.get("secondary_identifiers", {})
                ),
                developer_id=asset_data.get("developer_id"),
                publisher_name=asset_data.get("publisher_name"),
                display_name=asset_data["display_name"],
                handle=asset_data.get("handle"),
                description=asset_data.get("description"),
                canonical_url=asset_data.get("canonical_url"),
                icon_url=asset_data.get("icon_url"),
                icon_hash=asset_data.get("icon_hash"),
                relationship=asset_data["relationship"],
                verification_method=asset_data["verification_method"],
                is_verified=asset_data.get("is_verified", False),
                trust_publisher=asset_data.get("trust_publisher", False),
                is_active=asset_data.get("is_active", True),
                notes=asset_data.get("notes"),
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)
            result = self._to_dict(asset)

        if self.audit_repo:
            self.audit_repo.log(
                brand_id=asset.brand_id,
                actor_label=actor_label,
                event_type="OFFICIAL_ASSET_CREATED",
                entity_type="official_assets",
                entity_id=asset.id,
                details={
                    "display_name": asset.display_name,
                    "platform": asset.platform,
                },
            )

        return result

    def get(self, asset_id: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            asset = session.get(OfficialAsset, asset_id)
            return self._to_dict(asset) if asset else None

    def list_by_brand(
        self,
        brand_id: str,
        asset_type: str | None = None,
        relationship: str | None = None,
        is_verified: bool | None = None,
        is_active: bool | None = None,
    ) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            stmt = select(OfficialAsset).where(OfficialAsset.brand_id == brand_id)
            if asset_type is not None:
                stmt = stmt.where(OfficialAsset.asset_type == asset_type)
            if relationship is not None:
                stmt = stmt.where(OfficialAsset.relationship == relationship)
            if is_verified is not None:
                stmt = stmt.where(OfficialAsset.is_verified == is_verified)
            if is_active is not None:
                stmt = stmt.where(OfficialAsset.is_active == is_active)

            assets = session.scalars(stmt).all()
            return [self._to_dict(a) for a in assets]

    def update(
        self, asset_id: str, update_data: dict[str, Any], actor_label: str = "system"
    ) -> dict[str, Any] | None:
        with self.session_factory() as session:
            asset = session.get(OfficialAsset, asset_id)
            if not asset:
                return None
            for k, v in update_data.items():
                if hasattr(asset, k) and k not in ("id", "brand_id", "created_at"):
                    setattr(asset, k, copy.deepcopy(v))
            asset.updated_at = utc_now()
            session.commit()
            session.refresh(asset)
            result = self._to_dict(asset)

        if self.audit_repo:
            self.audit_repo.log(
                brand_id=result["brand_id"],
                actor_label=actor_label,
                event_type="OFFICIAL_ASSET_UPDATED",
                entity_type="official_assets",
                entity_id=asset_id,
                details=update_data,
            )

        return result


class SqlAlchemyScanRepo(ScanRepo):
    """SQLAlchemy implementation of ScanRepo."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def _to_dict(self, scan: Scan) -> dict[str, Any]:
        return {
            "id": scan.id,
            "brand_id": scan.brand_id,
            "mode": scan.mode,
            "status": scan.status,
            "stage": scan.stage,
            "progress_percent": scan.progress_percent,
            "options": scan.options,
            "source_outcomes": scan.source_outcomes,
            "funnel": scan.funnel,
            "findings_by_severity": scan.findings_by_severity,
            "events": scan.events,
            "error_message": scan.error_message,
            "created_at": scan.created_at,
            "started_at": scan.started_at,
            "completed_at": scan.completed_at,
        }

    def create(self, scan_data: dict[str, Any]) -> dict[str, Any]:
        with self.session_factory() as session:
            scan = Scan(
                id=scan_data.get("id") or generate_uuid(),
                brand_id=scan_data["brand_id"],
                mode=scan_data.get("mode", "LIVE"),
                status=scan_data.get("status", "QUEUED"),
                stage=scan_data.get("stage", "queued"),
                progress_percent=scan_data.get("progress_percent", 0),
                options=copy.deepcopy(scan_data.get("options", {})),
                source_outcomes=copy.deepcopy(scan_data.get("source_outcomes", [])),
                funnel=copy.deepcopy(scan_data.get("funnel", {})),
                findings_by_severity=copy.deepcopy(
                    scan_data.get("findings_by_severity", {})
                ),
                events=copy.deepcopy(scan_data.get("events", [])),
                error_message=scan_data.get("error_message"),
            )
            session.add(scan)
            session.commit()
            session.refresh(scan)
            return self._to_dict(scan)

    def get(self, scan_id: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            scan = session.get(Scan, scan_id)
            return self._to_dict(scan) if scan else None

    def list(
        self, brand_id: str, limit: int = 20, offset: int = 0
    ) -> Page[dict[str, Any]]:
        with self.session_factory() as session:
            count_stmt = select(func.count(Scan.id)).where(Scan.brand_id == brand_id)
            total = session.scalar(count_stmt) or 0

            stmt = (
                select(Scan)
                .where(Scan.brand_id == brand_id)
                .order_by(desc(Scan.created_at))
                .limit(limit)
                .offset(offset)
            )
            scans = session.scalars(stmt).all()
            return Page(
                items=[self._to_dict(s) for s in scans],
                total=total,
                limit=limit,
                offset=offset,
            )

    def update_progress(
        self, scan_id: str, stage: str, progress_percent: int
    ) -> dict[str, Any] | None:
        with self.session_factory() as session:
            scan = session.get(Scan, scan_id)
            if not scan:
                return None
            scan.stage = stage
            scan.progress_percent = progress_percent
            if scan.started_at is None and stage != "queued":
                scan.started_at = utc_now()
            session.commit()
            session.refresh(scan)
            return self._to_dict(scan)

    def append_event(self, scan_id: str, event_data: dict[str, Any]) -> None:
        with self.session_factory() as session:
            scan = session.get(Scan, scan_id)
            if not scan:
                return
            events = list(scan.events or [])
            events.append(copy.deepcopy(event_data))
            # Capped at 200 events
            if len(events) > 200:
                events = events[-200:]
            scan.events = events
            session.commit()

    def finish(
        self,
        scan_id: str,
        status: str,
        source_outcomes: list[Any],
        funnel: dict[str, Any],
        findings_by_severity: dict[str, int],
        error_message: str | None = None,
    ) -> dict[str, Any] | None:
        with self.session_factory() as session:
            scan = session.get(Scan, scan_id)
            if not scan:
                return None
            scan.status = status
            scan.stage = "completed" if "COMPLETED" in status else "failed"
            scan.progress_percent = 100
            scan.source_outcomes = copy.deepcopy(source_outcomes)
            scan.funnel = copy.deepcopy(funnel)
            scan.findings_by_severity = copy.deepcopy(findings_by_severity)
            scan.error_message = error_message
            scan.completed_at = utc_now()
            session.commit()
            session.refresh(scan)
            return self._to_dict(scan)


class SqlAlchemyCandidateRepo(CandidateRepo):
    """SQLAlchemy implementation of CandidateRepo with race-safe upsert."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def _to_dict(self, c: CandidateAsset) -> dict[str, Any]:
        return {
            "id": c.id,
            "brand_id": c.brand_id,
            "platform": c.platform,
            "asset_type": c.asset_type,
            "stable_identifier": c.stable_identifier,
            "secondary_identifiers": c.secondary_identifiers,
            "display_name": c.display_name,
            "handle": c.handle,
            "publisher_name": c.publisher_name,
            "developer_id": c.developer_id,
            "description": c.description,
            "category": c.category,
            "external_links": c.external_links,
            "icon_url": c.icon_url,
            "icon_hash": c.icon_hash,
            "canonical_url": c.canonical_url,
            "created_at_source": c.created_at_source,
            "followers": c.followers,
            "following": c.following,
            "posts_count": c.posts_count,
            "rating_count": c.rating_count,
            "last_source_mode": c.last_source_mode,
            "content_hash": c.content_hash,
            "analyst_status": c.analyst_status,
            "analyst_reason": c.analyst_reason,
            "first_seen_at": c.first_seen_at,
            "last_seen_at": c.last_seen_at,
            "last_scan_id": c.last_scan_id,
        }

    def upsert(self, candidate: Any, brand_id: str, scan_id: str) -> dict[str, Any]:
        platform = str(_extract(candidate, "platform"))
        stable_id = str(_extract(candidate, "stable_identifier"))
        display_name = _extract(candidate, "display_name") or ""
        publisher_name = _extract(candidate, "publisher_name")
        description = _extract(candidate, "description")
        icon_hash = _extract(candidate, "icon_hash")

        content_hash = compute_content_hash(
            display_name=display_name,
            publisher_name=publisher_name,
            description=description,
            icon_hash=icon_hash,
        )

        now = _utc_now()
        retrieved_at = _extract(candidate, "retrieved_at", now)

        with self.session_factory() as session:
            # 1. Select query inside transaction
            stmt = select(CandidateAsset).where(
                CandidateAsset.brand_id == str(brand_id),
                CandidateAsset.platform == platform,
                CandidateAsset.stable_identifier == stable_id,
            )
            existing = session.scalar(stmt)

            if existing:
                # Update observed fields, last_seen_at, last_scan_id, content_hash
                existing.display_name = display_name
                existing.handle = _extract(candidate, "handle")
                existing.publisher_name = publisher_name
                existing.developer_id = _extract(candidate, "developer_id")
                existing.description = description
                existing.category = _extract(candidate, "category")
                existing.external_links = copy.deepcopy(
                    _extract(candidate, "external_links", [])
                )
                existing.icon_url = _extract(candidate, "icon_url")
                existing.icon_hash = icon_hash
                existing.canonical_url = _extract(candidate, "canonical_url")
                existing.created_at_source = _extract(candidate, "created_at_source")
                existing.followers = _extract(candidate, "followers")
                existing.following = _extract(candidate, "following")
                existing.posts_count = _extract(candidate, "posts_count")
                existing.rating_count = _extract(candidate, "rating_count")
                existing.last_source_mode = str(
                    _extract(candidate, "source_mode", "LIVE")
                )
                existing.secondary_identifiers = copy.deepcopy(
                    _extract(candidate, "secondary_identifiers", {})
                )
                existing.content_hash = content_hash
                existing.last_seen_at = retrieved_at or now
                existing.last_scan_id = str(scan_id)
                # Decision memory: keeps first_seen_at, analyst_status, analyst_reason
                session.commit()
                session.refresh(existing)
                return self._to_dict(existing)

            # 2. Insert new record with savepoint fallback for race conditions
            new_cand = CandidateAsset(
                id=generate_uuid(),
                brand_id=str(brand_id),
                platform=platform,
                asset_type=str(_extract(candidate, "asset_type", "IOS_APP")),
                stable_identifier=stable_id,
                secondary_identifiers=copy.deepcopy(
                    _extract(candidate, "secondary_identifiers", {})
                ),
                display_name=display_name,
                handle=_extract(candidate, "handle"),
                publisher_name=publisher_name,
                developer_id=_extract(candidate, "developer_id"),
                description=description,
                category=_extract(candidate, "category"),
                external_links=copy.deepcopy(_extract(candidate, "external_links", [])),
                icon_url=_extract(candidate, "icon_url"),
                icon_hash=icon_hash,
                canonical_url=_extract(candidate, "canonical_url"),
                created_at_source=_extract(candidate, "created_at_source"),
                followers=_extract(candidate, "followers"),
                following=_extract(candidate, "following"),
                posts_count=_extract(candidate, "posts_count"),
                rating_count=_extract(candidate, "rating_count"),
                last_source_mode=str(_extract(candidate, "source_mode", "LIVE")),
                content_hash=content_hash,
                analyst_status="NEW",
                analyst_reason=None,
                first_seen_at=retrieved_at or now,
                last_seen_at=retrieved_at or now,
                last_scan_id=str(scan_id),
            )

            try:
                with session.begin_nested():
                    session.add(new_cand)
                    session.flush()
                session.commit()
                session.refresh(new_cand)
                return self._to_dict(new_cand)
            except IntegrityError:
                # Race condition: another thread inserted between select and insert
                existing = session.scalar(stmt)
                if not existing:
                    raise
                existing.display_name = display_name
                existing.publisher_name = publisher_name
                existing.description = description
                existing.icon_hash = icon_hash
                existing.content_hash = content_hash
                existing.last_seen_at = retrieved_at or now
                existing.last_scan_id = str(scan_id)
                session.commit()
                session.refresh(existing)
                return self._to_dict(existing)

    def get(self, candidate_id: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            cand = session.get(CandidateAsset, candidate_id)
            return self._to_dict(cand) if cand else None

    def get_by_stable_id(
        self, brand_id: str, platform: str, stable_identifier: str
    ) -> dict[str, Any] | None:
        with self.session_factory() as session:
            stmt = select(CandidateAsset).where(
                CandidateAsset.brand_id == str(brand_id),
                CandidateAsset.platform == str(platform),
                CandidateAsset.stable_identifier == str(stable_identifier),
            )
            cand = session.scalar(stmt)
            return self._to_dict(cand) if cand else None


class SqlAlchemyDecisionRepo(DecisionRepo):
    """SQLAlchemy implementation of DecisionRepo (atomic update, decision record, and audit log)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def record(
        self,
        candidate_id: str,
        assessment_id: str | None,
        new_status: str,
        decision_reason: str,
        notes: str | None = None,
        actor_label: str = "analyst",
    ) -> dict[str, Any]:
        # Domain validation: decision_reason is required for DISMISSED_FALSE_POSITIVE and CONFIRMED_SUSPICIOUS
        if new_status in ("DISMISSED_FALSE_POSITIVE", "CONFIRMED_SUSPICIOUS") and (
            not decision_reason or not decision_reason.strip()
        ):
            raise DomainValidationError(
                f"decision_reason is required for status '{new_status}'"
            )

        with self.session_factory() as session:
            with session.begin():
                candidate = session.get(CandidateAsset, candidate_id)
                if not candidate:
                    raise EntityNotFoundError(f"Candidate {candidate_id} not found")

                previous_status = candidate.analyst_status
                candidate.analyst_status = new_status
                candidate.analyst_reason = decision_reason

                dec_id = generate_uuid()
                decision = AnalystDecision(
                    id=dec_id,
                    candidate_asset_id=candidate_id,
                    assessment_id=assessment_id,
                    previous_status=previous_status,
                    new_status=new_status,
                    decision_reason=decision_reason,
                    notes=notes,
                    actor_label=actor_label or "analyst",
                    created_at=utc_now(),
                )
                session.add(decision)

                # Write audit event in the same atomic transaction
                audit = AuditEvent(
                    id=generate_uuid(),
                    brand_id=candidate.brand_id,
                    actor_label=actor_label or "analyst",
                    event_type="ANALYST_DECISION",
                    entity_type="candidate_assets",
                    entity_id=candidate_id,
                    details={
                        "previous_status": previous_status,
                        "new_status": new_status,
                        "decision_reason": decision_reason,
                        "assessment_id": assessment_id,
                        "content_hash_at_decision": candidate.content_hash,
                    },
                    created_at=utc_now(),
                )
                session.add(audit)

            # Query decision after commit
            decision_row = session.get(AnalystDecision, dec_id)
            return {
                "id": decision_row.id,
                "candidate_asset_id": decision_row.candidate_asset_id,
                "assessment_id": decision_row.assessment_id,
                "previous_status": decision_row.previous_status,
                "new_status": decision_row.new_status,
                "decision_reason": decision_row.decision_reason,
                "notes": decision_row.notes,
                "actor_label": decision_row.actor_label,
                "created_at": decision_row.created_at,
            }

    def list_by_candidate(self, candidate_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            stmt = (
                select(AnalystDecision)
                .where(AnalystDecision.candidate_asset_id == candidate_id)
                .order_by(desc(AnalystDecision.created_at))
            )
            rows = session.scalars(stmt).all()
            return [
                {
                    "id": r.id,
                    "candidate_asset_id": r.candidate_asset_id,
                    "assessment_id": r.assessment_id,
                    "previous_status": r.previous_status,
                    "new_status": r.new_status,
                    "decision_reason": r.decision_reason,
                    "notes": r.notes,
                    "actor_label": r.actor_label,
                    "created_at": r.created_at,
                }
                for r in rows
            ]


class SqlAlchemyCacheRepo(CacheRepo):
    """SQLAlchemy implementation of CacheRepo with TTL awareness."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def get(self, key: str, max_age_s: int | None = None) -> CachedResponse | None:
        with self.session_factory() as session:
            item = session.get(ResponseCache, key)
            if not item:
                return None

            age_s = (_utc_now() - item.retrieved_at).total_seconds()

            # TTL & max_age_s enforcement:
            # If max_age_s is specified, item must be strictly fresher than both max_age_s and ttl_seconds
            if max_age_s is not None:
                if max_age_s <= 0:
                    return None
                if age_s > max_age_s or age_s > item.ttl_seconds:
                    return None

            # If max_age_s is None: stale read is allowed; keep original retrieved_at
            return CachedResponse(
                key=item.key,
                source_id=item.source_id,
                request=copy.deepcopy(item.request),
                response=copy.deepcopy(item.response),
                retrieved_at=item.retrieved_at,
                ttl_seconds=item.ttl_seconds,
            )

    def put(
        self,
        key: str,
        source_id: str,
        request: dict[str, Any],
        response: dict[str, Any],
        ttl_seconds: int = 3600,
    ) -> None:
        with self.session_factory() as session:
            existing = session.get(ResponseCache, key)
            now = utc_now()
            if existing:
                existing.source_id = source_id
                existing.request = copy.deepcopy(request)
                existing.response = copy.deepcopy(response)
                existing.retrieved_at = now
                existing.ttl_seconds = ttl_seconds
            else:
                new_item = ResponseCache(
                    key=key,
                    source_id=source_id,
                    request=copy.deepcopy(request),
                    response=copy.deepcopy(response),
                    retrieved_at=now,
                    ttl_seconds=ttl_seconds,
                )
                session.add(new_item)
            session.commit()


class SqlAlchemyAssessmentRepo(AssessmentRepo):
    """SQLAlchemy implementation of AssessmentRepo."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(
        self,
        scan_id: str,
        candidate_id: str,
        result: Any,
        evidence: Sequence[Any],
        brand_id: str | None = None,
    ) -> str:
        with self.session_factory() as session:
            cand = session.get(CandidateAsset, candidate_id)
            resolved_brand_id = brand_id or (cand.brand_id if cand else "")

            breakdown = _extract(result, "score_breakdown") or _extract(
                result, "breakdown", []
            )
            corroborating = _extract(result, "corroborating_groups", [])
            gates = _extract(result, "gates_applied", [])

            ass_id = generate_uuid()
            assessment = Assessment(
                id=ass_id,
                scan_id=str(scan_id),
                brand_id=str(resolved_brand_id),
                candidate_asset_id=str(candidate_id),
                identity_decision=str(_extract(result, "identity_decision")),
                rule=str(_extract(result, "rule", "")),
                matched_official_asset_id=_extract(result, "matched_official_asset_id"),
                risk_score=_extract(result, "risk_score"),
                severity=_extract(result, "severity"),
                evidence_coverage=_extract(result, "evidence_coverage"),
                corroborating_groups=copy.deepcopy(corroborating),
                gates_applied=copy.deepcopy(gates),
                score_breakdown=copy.deepcopy(breakdown),
                technique=str(_extract(result, "technique", "NONE")),
                explanation=str(_extract(result, "explanation", "")),
                source_mode=str(_extract(result, "source_mode", "LIVE")),
                scoring_version=str(_extract(result, "scoring_version", "3.0.0")),
                nearest_official_asset_id=_extract(result, "nearest_official_asset_id"),
                created_at=utc_now(),
            )
            session.add(assessment)

            for ev in evidence:
                ev_row = Evidence(
                    id=generate_uuid(),
                    assessment_id=ass_id,
                    candidate_asset_id=str(candidate_id),
                    scan_id=str(scan_id),
                    source_id=str(_extract(ev, "source_id")),
                    evidence_type=str(_extract(ev, "evidence_type")),
                    status=str(_extract(ev, "status", "OBSERVED")),
                    field_name=str(_extract(ev, "field_name")),
                    observed_value=_extract(ev, "observed_value"),
                    source_url=_extract(ev, "source_url"),
                    observed_at=_extract(ev, "observed_at", utc_now()),
                    notes=_extract(ev, "notes"),
                )
                session.add(ev_row)

            session.commit()
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
        with self.session_factory() as session:
            # Query newest assessment per candidate in a SINGLE SQL query via window function
            if latest_only:
                subq = select(
                    Assessment.id.label("assessment_id"),
                    func.row_number()
                    .over(
                        partition_by=Assessment.candidate_asset_id,
                        order_by=desc(Assessment.created_at),
                    )
                    .label("rn"),
                ).where(Assessment.identity_decision == "CANDIDATE_FOR_REVIEW")
                if brand_id:
                    subq = subq.where(Assessment.brand_id == brand_id)
                if scan_id:
                    subq = subq.where(Assessment.scan_id == scan_id)
                subq = subq.subquery()

                base_stmt = (
                    select(Assessment, CandidateAsset)
                    .join(
                        CandidateAsset,
                        Assessment.candidate_asset_id == CandidateAsset.id,
                    )
                    .join(subq, Assessment.id == subq.c.assessment_id)
                    .where(subq.c.rn == 1)
                )
            else:
                base_stmt = (
                    select(Assessment, CandidateAsset)
                    .join(
                        CandidateAsset,
                        Assessment.candidate_asset_id == CandidateAsset.id,
                    )
                    .where(Assessment.identity_decision == "CANDIDATE_FOR_REVIEW")
                )
                if brand_id:
                    base_stmt = base_stmt.where(Assessment.brand_id == brand_id)
                if scan_id:
                    base_stmt = base_stmt.where(Assessment.scan_id == scan_id)

            # Apply candidate and assessment filters
            if severity:
                base_stmt = base_stmt.where(Assessment.severity == severity)
            if min_score is not None:
                base_stmt = base_stmt.where(Assessment.risk_score >= min_score)
            if source_mode:
                base_stmt = base_stmt.where(Assessment.source_mode == source_mode)
            if status:
                base_stmt = base_stmt.where(CandidateAsset.analyst_status == status)
            if asset_type:
                base_stmt = base_stmt.where(CandidateAsset.asset_type == asset_type)
            if platform:
                base_stmt = base_stmt.where(CandidateAsset.platform == platform)
            if q:
                pattern = f"%{q.lower()}%"
                base_stmt = base_stmt.where(
                    func.lower(CandidateAsset.display_name).like(pattern)
                    | func.lower(CandidateAsset.publisher_name).like(pattern)
                    | func.lower(CandidateAsset.handle).like(pattern)
                )

            # Fetch candidates and assessments
            rows = session.execute(base_stmt).all()

            # Query latest decision audit details to compute changed_since_decision
            cand_ids = [cand.id for _, cand in rows]
            hash_at_decision_map: dict[str, str] = {}
            if cand_ids:
                audit_stmt = (
                    select(AuditEvent)
                    .where(
                        AuditEvent.entity_type == "candidate_assets",
                        AuditEvent.entity_id.in_(cand_ids),
                        AuditEvent.event_type == "ANALYST_DECISION",
                    )
                    .order_by(desc(AuditEvent.created_at))
                )
                audit_rows = session.scalars(audit_stmt).all()
                for a in audit_rows:
                    if a.entity_id not in hash_at_decision_map:
                        hash_at_decision_map[a.entity_id] = (a.details or {}).get(
                            "content_hash_at_decision", ""
                        )

            records: list[FindingRecord] = []
            for ass, cand in rows:
                is_dismissed = cand.analyst_status == "DISMISSED_FALSE_POSITIVE"
                dec_hash = hash_at_decision_map.get(cand.id)
                changed_since_decision = bool(
                    dec_hash and dec_hash != cand.content_hash
                )

                if (
                    is_dismissed
                    and not include_dismissed
                    and not changed_since_decision
                ):
                    continue

                cand_summary = {
                    "platform": cand.platform,
                    "asset_type": cand.asset_type,
                    "stable_identifier": cand.stable_identifier,
                    "display_name": cand.display_name,
                    "handle": cand.handle,
                    "publisher_name": cand.publisher_name,
                    "icon_url": cand.icon_url,
                    "canonical_url": cand.canonical_url,
                }

                top_signals = []
                for item in ass.score_breakdown or []:
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
                    id=ass.id,
                    brand_id=ass.brand_id,
                    scan_id=ass.scan_id,
                    candidate=cand_summary,
                    risk_score=ass.risk_score,
                    severity=ass.severity,
                    evidence_coverage=ass.evidence_coverage,
                    technique=ass.technique,
                    top_signals=top_signals,
                    status=cand.analyst_status,
                    source_mode=ass.source_mode,
                    observed_at=cand.last_seen_at,
                    changed_since_decision=changed_since_decision,
                    candidate_asset_id=cand.id,
                )
                records.append(rec)

            # Sort records: score_desc | score_asc | seen_desc | name_asc
            if sort == "score_asc":
                records.sort(key=lambda r: r.risk_score or 0)
            elif sort == "seen_desc":
                records.sort(key=lambda r: r.observed_at or _utc_now(), reverse=True)
            elif sort == "name_asc":
                records.sort(
                    key=lambda r: (r.candidate.get("display_name") or "").lower()
                )
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
        with self.session_factory() as session:
            stmt = (
                select(Assessment, CandidateAsset)
                .join(
                    CandidateAsset,
                    Assessment.candidate_asset_id == CandidateAsset.id,
                )
                .where(Assessment.identity_decision != "CANDIDATE_FOR_REVIEW")
            )
            if brand_id:
                stmt = stmt.where(Assessment.brand_id == brand_id)
            if decision:
                stmt = stmt.where(Assessment.identity_decision == decision)
            if scan_id:
                stmt = stmt.where(Assessment.scan_id == scan_id)
            if platform:
                stmt = stmt.where(CandidateAsset.platform == platform)
            if q:
                pattern = f"%{q.lower()}%"
                stmt = stmt.where(
                    func.lower(CandidateAsset.display_name).like(pattern)
                    | func.lower(CandidateAsset.publisher_name).like(pattern)
                )

            stmt = stmt.order_by(desc(Assessment.created_at))
            rows = session.execute(stmt).all()

            records: list[ClearedRecord] = []
            for ass, cand in rows:
                cand_summary = {
                    "platform": cand.platform,
                    "asset_type": cand.asset_type,
                    "stable_identifier": cand.stable_identifier,
                    "display_name": cand.display_name,
                    "publisher_name": cand.publisher_name,
                    "icon_url": cand.icon_url,
                }
                rec = ClearedRecord(
                    id=ass.id,
                    scan_id=ass.scan_id,
                    candidate=cand_summary,
                    decision=ass.identity_decision,
                    rule=ass.rule,
                    matched_official_asset_id=ass.matched_official_asset_id,
                    explanation=ass.explanation,
                    risk_score=ass.risk_score,
                    source_mode=ass.source_mode,
                    observed_at=cand.last_seen_at,
                    candidate_asset_id=cand.id,
                )
                records.append(rec)

            total = len(records)
            paginated = records[offset : offset + limit]
            return Page(items=paginated, total=total, limit=limit, offset=offset)
