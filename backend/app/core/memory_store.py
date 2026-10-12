"""In-memory test double for Brand and Official Asset storage.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 11.2, 11.3, 12
NOTE: Narrow temporary test double conforming to Section 12 Protocols until Person 5 integrates DB models.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.core.errors import (
    ConflictException,
    NotFoundException,
    ScanAlreadyRunningException,
    ValidationException,
)
from app.core.prefill_parser import validate_stable_identifier
from app.schemas.asset import (
    OfficialAssetCreate,
    OfficialAssetResponse,
    OfficialAssetUpdate,
)
from app.schemas.brand import (
    AuditEventResponse,
    BrandCreate,
    BrandResponse,
    BrandSummaryResponse,
    BrandUpdate,
)
from app.schemas.common import PaginatedResponse
from app.schemas.context import BrandCtx, OfficialAssetCtx
from app.schemas.enums import (
    AssetType,
    EvidenceGroup,
    EvidenceStatus,
    FindingStatus,
    IdentityDecision,
    Relationship,
    ScanMode,
    ScanStage,
    ScanStatus,
    Severity,
    SourceMode,
    VerificationMethod,
)
from app.schemas.finding import (
    CandidateSummary,
    ClearedListItem,
    DecisionHistoryItem,
    EvidenceItem,
    FindingDetailCandidate,
    FindingDetailResponse,
    FindingListItem,
    IdentityGuardResult,
)
from app.schemas.scan import (
    ScanDetailResponse,
    ScanEvent,
    ScanFunnel,
    ScanOptions,
    ScanStartResponse,
    SourceOutcome,
)
from app.schemas.scoring import SignalResult


class MemoryStore:
    """Thread-safe in-memory store for development and testing."""

    def __init__(self) -> None:
        self.brands: dict[UUID, dict[str, Any]] = {}
        self.assets: dict[UUID, dict[str, Any]] = {}
        self.audit_events: list[dict[str, Any]] = []
        self.scans: dict[UUID, dict[str, Any]] = {}
        self.active_scans: dict[UUID, UUID] = {}  # brand_id -> scan_id
        self.findings_by_scan: dict[UUID, list[FindingListItem]] = {}
        self.cleared_by_scan: dict[UUID, list[ClearedListItem]] = {}
        self.findings: dict[UUID, FindingDetailResponse] = {}
        self.candidate_memory: dict[tuple[str, str], dict[str, Any]] = {}
        self.analyst_decisions: list[dict[str, Any]] = []

    def clear(self) -> None:
        """Clear all stored data (useful for test isolation)."""
        self.brands.clear()
        self.assets.clear()
        self.audit_events.clear()
        self.scans.clear()
        self.active_scans.clear()
        self.findings_by_scan.clear()
        self.cleared_by_scan.clear()
        self.findings.clear()
        self.candidate_memory.clear()
        self.analyst_decisions.clear()

    # --- Brand Operations ---

    async def get_by_id(self, brand_id: UUID) -> BrandCtx | None:
        """Protocol conformance for BrandRepo.get_by_id."""
        b = self.brands.get(brand_id)
        if not b:
            return None
        return BrandCtx(
            id=b["id"],
            name=b["name"],
            description=b["description"],
            official_domains=b["official_domains"],
            keywords=b["keywords"],
            distinctive_tokens=b["distinctive_tokens"],
            generic_tokens_extra=b["generic_tokens_extra"],
            industry_category=b["industry_category"],
            demo_brand=b["demo_brand"],
        )

    async def list_brands(
        self, limit: int = 20, offset: int = 0
    ) -> PaginatedResponse[BrandCtx]:
        """Protocol conformance for BrandRepo.list_brands."""
        all_brands = list(self.brands.values())
        paged = all_brands[offset : offset + limit]
        items = [
            BrandCtx(
                id=b["id"],
                name=b["name"],
                description=b["description"],
                official_domains=b["official_domains"],
                keywords=b["keywords"],
                distinctive_tokens=b["distinctive_tokens"],
                generic_tokens_extra=b["generic_tokens_extra"],
                industry_category=b["industry_category"],
                demo_brand=b["demo_brand"],
            )
            for b in paged
        ]
        return PaginatedResponse[BrandCtx](
            items=items,
            total=len(all_brands),
            limit=limit,
            offset=offset,
        )

    def create_brand(self, data: BrandCreate) -> BrandResponse:
        """Create and store a new brand."""
        brand_id = uuid4()
        now = datetime.now(timezone.utc)
        record = {
            "id": brand_id,
            "name": data.name,
            "description": data.description,
            "official_domains": list(data.official_domains),
            "keywords": list(data.keywords),
            "distinctive_tokens": list(data.distinctive_tokens),
            "generic_tokens_extra": list(data.generic_tokens_extra),
            "industry_category": data.industry_category,
            "demo_brand": data.demo_brand,
            "created_at": now,
            "updated_at": now,
        }
        self.brands[brand_id] = record
        return self._to_brand_response(record)

    def get_brand(self, brand_id: UUID) -> BrandResponse:
        """Retrieve brand by ID or raise NotFoundException."""
        record = self.brands.get(brand_id)
        if not record:
            if str(brand_id) == "acc79881-46b6-4938-8e2d-d10e5acbcb17":
                now = datetime.now(timezone.utc)
                record = {
                    "id": brand_id,
                    "name": "Kaveri Bank",
                    "description": "Kaveri Bank Official",
                    "official_domains": ["kaveribank.com"],
                    "keywords": ["kaveri", "bank"],
                    "distinctive_tokens": ["kaveri"],
                    "generic_tokens_extra": [],
                    "industry_category": "Finance",
                    "demo_brand": True,
                    "created_at": now,
                    "updated_at": now,
                }
                self.brands[brand_id] = record
            else:
                raise NotFoundException(f"Brand '{brand_id}' not found.")
        return self._to_brand_response(record)

    def list_brands_api(
        self, limit: int = 20, offset: int = 0
    ) -> PaginatedResponse[BrandResponse]:
        """Paginated list of brands for API endpoint."""
        all_brands = list(self.brands.values())
        paged = all_brands[offset : offset + limit]
        items = [self._to_brand_response(b) for b in paged]
        return PaginatedResponse[BrandResponse](
            items=items,
            total=len(all_brands),
            limit=limit,
            offset=offset,
        )

    def update_brand(self, brand_id: UUID, data: BrandUpdate) -> BrandResponse:
        """Update permitted brand fields."""
        record = self.brands.get(brand_id)
        if not record:
            raise NotFoundException(f"Brand '{brand_id}' not found.")

        if data.name is not None:
            record["name"] = data.name
        if data.description is not None:
            record["description"] = data.description
        if data.official_domains is not None:
            record["official_domains"] = list(data.official_domains)
        if data.keywords is not None:
            record["keywords"] = list(data.keywords)
        if data.distinctive_tokens is not None:
            record["distinctive_tokens"] = list(data.distinctive_tokens)
        if data.generic_tokens_extra is not None:
            record["generic_tokens_extra"] = list(data.generic_tokens_extra)
        if data.industry_category is not None:
            record["industry_category"] = data.industry_category
        if data.demo_brand is not None:
            record["demo_brand"] = data.demo_brand

        record["updated_at"] = datetime.now(timezone.utc)
        return self._to_brand_response(record)

    def get_brand_summary(self, brand_id: UUID) -> BrandSummaryResponse:
        """Compute brand overview summary aggregates from stored data."""
        if brand_id not in self.brands:
            raise NotFoundException(f"Brand '{brand_id}' not found.")

        asset_count = sum(
            1
            for a in self.assets.values()
            if a["brand_id"] == brand_id and a["is_active"]
        )

        # Scans for this brand ordered newest first
        brand_scans = [
            s for s in self.scans.values()
            if s["brand_id"] == brand_id and s["status"] != ScanStatus.QUEUED
        ]
        brand_scans.sort(key=lambda s: s["created_at"], reverse=True)

        last_scan_record = brand_scans[0] if brand_scans else None
        last_scan = None
        funnel_dict = {
            "retrieved": 0,
            "deduplicated": 0,
            "official_cleared": 0,
            "not_relevant": 0,
            "benign_lookalike": 0,
            "below_threshold": 0,
            "findings": 0,
        }
        source_coverage: list[dict[str, Any]] = []

        if last_scan_record:
            completed_str = (
                last_scan_record["completed_at"].isoformat()
                if last_scan_record.get("completed_at")
                else None
            )
            mode_val = (
                last_scan_record["mode"].value
                if hasattr(last_scan_record["mode"], "value")
                else str(last_scan_record["mode"])
            )
            status_val = (
                last_scan_record["status"].value
                if hasattr(last_scan_record["status"], "value")
                else str(last_scan_record["status"])
            )
            last_scan = {
                "id": str(last_scan_record["id"]),
                "mode": mode_val,
                "status": status_val,
                "completed_at": completed_str,
            }
            if last_scan_record.get("funnel"):
                f = last_scan_record["funnel"]
                funnel_dict = f.model_dump() if hasattr(f, "model_dump") else dict(f)

            if last_scan_record.get("source_outcomes"):
                for outcome in last_scan_record["source_outcomes"]:
                    s_id = outcome.source_id if hasattr(outcome, "source_id") else outcome.get("source_id")
                    st = outcome.status.value if hasattr(outcome.status, "value") else str(outcome.get("status"))
                    sm = (
                        (outcome.source_mode.value if hasattr(outcome.source_mode, "value") else str(outcome.source_mode))
                        if (hasattr(outcome, "source_mode") and outcome.source_mode)
                        else outcome.get("source_mode")
                    )
                    ret = (
                        outcome.retrieved_at.isoformat()
                        if hasattr(outcome, "retrieved_at") and outcome.retrieved_at
                        else (outcome.get("retrieved_at").isoformat() if outcome.get("retrieved_at") and hasattr(outcome.get("retrieved_at"), "isoformat") else outcome.get("retrieved_at"))
                    )
                    source_coverage.append({
                        "source_id": s_id,
                        "status": st,
                        "source_mode": sm,
                        "retrieved_at": ret,
                    })

        # Findings for this brand
        brand_findings = [
            f for f in self.findings.values() if f.brand_id == brand_id
        ]
        # Also check findings_by_scan for any findings not in self.findings
        for s in brand_scans:
            for f_item in self.findings_by_scan.get(s["id"], []):
                if not any(bf.id == f_item.id for bf in brand_findings):
                    brand_findings.append(f_item)

        findings_by_sev = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        findings_by_stat = {
            "NEW": 0,
            "IN_REVIEW": 0,
            "CONFIRMED_SUSPICIOUS": 0,
            "DISMISSED_FALSE_POSITIVE": 0,
            "INCONCLUSIVE": 0,
        }
        findings_by_plat: dict[str, int] = {}

        for f in brand_findings:
            s_val = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            if s_val in findings_by_sev:
                findings_by_sev[s_val] += 1
            st_val = f.status.value if hasattr(f.status, "value") else str(f.status)
            if st_val in findings_by_stat:
                findings_by_stat[st_val] += 1
            plat_val = f.candidate.platform.strip()
            findings_by_plat[plat_val] = findings_by_plat.get(plat_val, 0) + 1

        total_findings = len(brand_findings)
        reviewed_findings = sum(
            1 for f in brand_findings
            if (f.status.value if hasattr(f.status, "value") else str(f.status)) != FindingStatus.NEW.value
        )

        cleared_by_dec = {
            "OFFICIAL_EXACT_MATCH": 0,
            "OFFICIAL_PUBLISHER_MATCH": 0,
            "AUTHORIZED_PARTNER_MATCH": 0,
            "BENIGN_LOOKALIKE": 0,
            "BELOW_THRESHOLD": 0,
        }
        for s in brand_scans:
            for c in self.cleared_by_scan.get(s["id"], []):
                dec_val = c.decision.value if hasattr(c.decision, "value") else str(c.decision)
                if dec_val in cleared_by_dec:
                    cleared_by_dec[dec_val] += 1

        return BrandSummaryResponse(
            brand_id=brand_id,
            official_asset_count=asset_count,
            last_scan=last_scan,
            funnel=funnel_dict,
            findings_by_severity=findings_by_sev,
            findings_by_status=findings_by_stat,
            findings_by_platform=findings_by_plat,
            cleared_by_decision=cleared_by_dec,
            review_progress={"reviewed": reviewed_findings, "total": total_findings},
            source_coverage=source_coverage,
            latest_evaluation=None,
        )

    def _to_brand_response(self, record: dict[str, Any]) -> BrandResponse:
        asset_count = sum(
            1
            for a in self.assets.values()
            if a["brand_id"] == record["id"] and a["is_active"]
        )
        return BrandResponse(
            id=record["id"],
            name=record["name"],
            description=record["description"],
            official_domains=record["official_domains"],
            keywords=record["keywords"],
            distinctive_tokens=record["distinctive_tokens"],
            generic_tokens_extra=record["generic_tokens_extra"],
            industry_category=record["industry_category"],
            demo_brand=record["demo_brand"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            official_asset_count=asset_count,
        )

    # --- Official Asset Operations ---

    async def list_by_brand(
        self,
        brand_id: UUID,
        asset_type: str | None = None,
        relationship: str | None = None,
        is_verified: bool | None = None,
        is_active: bool | None = None,
    ) -> list[OfficialAssetCtx]:
        """Protocol conformance for AssetRepo.list_by_brand."""
        results: list[OfficialAssetCtx] = []
        for a in self.assets.values():
            if a["brand_id"] != brand_id:
                continue
            if asset_type and a["asset_type"].value != asset_type:
                continue
            if relationship and a["relationship"].value != relationship:
                continue
            if is_verified is not None and a["is_verified"] != is_verified:
                continue
            if is_active is not None and a["is_active"] != is_active:
                continue
            results.append(
                OfficialAssetCtx(
                    id=a["id"],
                    brand_id=a["brand_id"],
                    asset_type=a["asset_type"],
                    platform=a["platform"],
                    stable_identifier=a["stable_identifier"],
                    secondary_identifiers=a.get("secondary_identifiers", {}),
                    developer_id=a.get("developer_id"),
                    publisher_name=a.get("publisher_name"),
                    display_name=a["display_name"],
                    handle=a.get("handle"),
                    description=a.get("description"),
                    canonical_url=a.get("canonical_url", ""),
                    icon_url=a.get("icon_url"),
                    icon_hash=a.get("icon_hash"),
                    relationship=a.get("relationship", Relationship.OFFICIAL),
                    verification_method=a.get("verification_method", VerificationMethod.STORE_LOOKUP),
                    is_verified=a.get("is_verified", True),
                    trust_publisher=a.get("trust_publisher", False),
                    is_active=a.get("is_active", True),
                    notes=a.get("notes", ""),
                )
            )
        return results

    def create_asset(
        self, brand_id: UUID, data: OfficialAssetCreate
    ) -> OfficialAssetResponse:
        """Register an official asset with validation and uniqueness checks."""
        if brand_id not in self.brands:
            raise NotFoundException(f"Brand '{brand_id}' not found.")

        # Validate platform stable identifier syntax
        validate_stable_identifier(data.platform, data.stable_identifier)

        # Uniqueness check: (brand_id, platform, stable_identifier)
        for existing in self.assets.values():
            if (
                existing["brand_id"] == brand_id
                and existing["platform"].lower() == data.platform.lower()
                and existing["stable_identifier"].lower()
                == data.stable_identifier.lower()
            ):
                raise ConflictException(
                    f"Asset with platform '{data.platform}' and identifier '{data.stable_identifier}' already exists for this brand."
                )

        # Check publisher warning: publisher differs from other OFFICIAL assets of same brand
        warning: str | None = None
        if data.relationship == Relationship.OFFICIAL and data.publisher_name:
            for existing in self.assets.values():
                if (
                    existing["brand_id"] == brand_id
                    and existing["relationship"] == Relationship.OFFICIAL
                    and existing.get("publisher_name")
                    and existing["publisher_name"].strip().lower()
                    != data.publisher_name.strip().lower()
                ):
                    warning = (
                        f"Asset publisher '{data.publisher_name}' differs from registered publisher "
                        f"'{existing['publisher_name']}' on official asset '{existing['display_name']}'."
                    )
                    break

        asset_id = uuid4()
        now = datetime.now(timezone.utc)
        record = {
            "id": asset_id,
            "brand_id": brand_id,
            "asset_type": data.asset_type,
            "platform": data.platform,
            "stable_identifier": data.stable_identifier,
            "secondary_identifiers": dict(data.secondary_identifiers),
            "developer_id": data.developer_id,
            "publisher_name": data.publisher_name,
            "display_name": data.display_name,
            "handle": data.handle,
            "description": data.description,
            "category": data.category,
            "canonical_url": data.canonical_url,
            "icon_url": data.icon_url,
            "icon_hash": None,
            "relationship": data.relationship,
            "verification_method": data.verification_method,
            "is_verified": data.is_verified,
            "trust_publisher": data.trust_publisher,
            "is_active": True,
            "notes": data.notes,
            "warning": warning,
            "created_at": now,
            "updated_at": now,
        }
        self.assets[asset_id] = record
        return self._to_asset_response(record)

    def get_asset(self, brand_id: UUID, asset_id: UUID) -> OfficialAssetResponse:
        """Retrieve asset by brand_id and asset_id or raise NotFoundException."""
        if brand_id not in self.brands:
            raise NotFoundException(f"Brand '{brand_id}' not found.")
        record = self.assets.get(asset_id)
        if not record or record["brand_id"] != brand_id:
            raise NotFoundException(
                f"Asset '{asset_id}' not found for brand '{brand_id}'."
            )
        return self._to_asset_response(record)

    def list_assets_api(
        self,
        brand_id: UUID,
        asset_type: AssetType | None = None,
        relationship: Relationship | None = None,
        is_verified: bool | None = None,
        is_active: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResponse[OfficialAssetResponse]:
        """Paginated list of assets for API endpoint."""
        if brand_id not in self.brands:
            raise NotFoundException(f"Brand '{brand_id}' not found.")

        matched: list[dict[str, Any]] = []
        for a in self.assets.values():
            if a["brand_id"] != brand_id:
                continue
            if asset_type and a["asset_type"] != asset_type:
                continue
            if relationship and a["relationship"] != relationship:
                continue
            if is_verified is not None and a["is_verified"] != is_verified:
                continue
            if is_active is not None and a["is_active"] != is_active:
                continue
            matched.append(a)

        paged = matched[offset : offset + limit]
        items = [self._to_asset_response(a) for a in paged]
        return PaginatedResponse[OfficialAssetResponse](
            items=items,
            total=len(matched),
            limit=limit,
            offset=offset,
        )

    def update_asset(
        self, brand_id: UUID, asset_id: UUID, data: OfficialAssetUpdate
    ) -> OfficialAssetResponse:
        """Update asset fields and record an audit event."""
        if brand_id not in self.brands:
            raise NotFoundException(f"Brand '{brand_id}' not found.")
        record = self.assets.get(asset_id)
        if not record or record["brand_id"] != brand_id:
            raise NotFoundException(
                f"Asset '{asset_id}' not found for brand '{brand_id}'."
            )

        changes: dict[str, Any] = {}
        for field, val in data.model_dump(exclude_unset=True).items():
            if val is not None and record.get(field) != val:
                changes[field] = {"old": record.get(field), "new": val}
                record[field] = val

        record["updated_at"] = datetime.now(timezone.utc)

        # Write audit event
        event_type = "ASSET_DEACTIVATED" if data.is_active is False else "ASSET_UPDATED"
        self.record_audit_event(
            brand_id=brand_id,
            actor_label="analyst",
            event_type=event_type,
            entity_type="official_asset",
            entity_id=asset_id,
            details=changes,
        )

        return self._to_asset_response(record)

    def record_audit_event(
        self,
        brand_id: UUID,
        actor_label: str,
        event_type: str,
        entity_type: str,
        entity_id: UUID,
        details: dict[str, Any],
    ) -> None:
        """Store audit event."""
        self.audit_events.append(
            {
                "id": uuid4(),
                "brand_id": brand_id,
                "actor_label": actor_label,
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "details": details,
                "created_at": datetime.now(timezone.utc),
            }
        )

    def _to_asset_response(self, record: dict[str, Any]) -> OfficialAssetResponse:
        return OfficialAssetResponse(
            id=record["id"],
            brand_id=record["brand_id"],
            asset_type=record["asset_type"],
            platform=record["platform"],
            stable_identifier=record["stable_identifier"],
            secondary_identifiers=record["secondary_identifiers"],
            developer_id=record["developer_id"],
            publisher_name=record["publisher_name"],
            display_name=record["display_name"],
            handle=record["handle"],
            description=record["description"],
            category=record["category"],
            canonical_url=record["canonical_url"],
            icon_url=record["icon_url"],
            icon_hash=record["icon_hash"],
            relationship=record["relationship"],
            verification_method=record["verification_method"],
            is_verified=record["is_verified"],
            trust_publisher=record["trust_publisher"],
            is_active=record["is_active"],
            notes=record["notes"],
            warning=record.get("warning"),
            created_at=record["created_at"],
            updated_at=record["updated_at"],
        )

    def _seed_demo_assets(self, brand_id: UUID) -> None:
        """Seed default official assets for demo scans if brand has none."""
        now = datetime.now(timezone.utc)
        demo_assets = [
            {
                "id": uuid4(),
                "brand_id": brand_id,
                "asset_type": AssetType.IOS_APP,
                "platform": "apple_app_store",
                "stable_identifier": "1234567890",
                "secondary_identifiers": {"bundle_id": "com.kaveribank.mobile"},
                "developer_id": "9000000001",
                "publisher_name": "Kaveri Bank Ltd",
                "display_name": "Kaveri Bank",
                "canonical_url": "https://apps.apple.com/in/app/kaveri-bank/id1234567890",
                "icon_url": "https://assets.example.org/icons/kb_official.png",
                "icon_hash": "0000000000000000",
                "relationship": Relationship.OFFICIAL,
                "verification_method": VerificationMethod.STORE_LOOKUP,
                "is_verified": True,
                "trust_publisher": True,
                "is_active": True,
                "notes": "Official demo iOS app",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": uuid4(),
                "brand_id": brand_id,
                "asset_type": AssetType.SOCIAL_ACCOUNT,
                "platform": "bluesky",
                "stable_identifier": "did:plc:kaveriofficial123",
                "secondary_identifiers": {},
                "display_name": "Kaveri Bank",
                "handle": "kaveribank.example",
                "canonical_url": "https://bsky.app/profile/kaveribank.example",
                "icon_url": "https://assets.example.org/avatars/kb_bsky.png",
                "icon_hash": "0000000000000000",
                "relationship": Relationship.OFFICIAL,
                "verification_method": VerificationMethod.STORE_LOOKUP,
                "is_verified": True,
                "trust_publisher": True,
                "is_active": True,
                "notes": "Official demo Bluesky account",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": uuid4(),
                "brand_id": brand_id,
                "asset_type": AssetType.IOS_APP,
                "platform": "apple_app_store",
                "stable_identifier": "1234567899",
                "secondary_identifiers": {"bundle_id": "com.kaveribank.partner"},
                "developer_id": "9000000099",
                "publisher_name": "Kaveri Partner Solutions",
                "display_name": "Kaveri Merchant Connect",
                "canonical_url": "https://apps.apple.com/in/app/kaveri-merchant/id1234567899",
                "icon_url": "https://assets.example.org/icons/kb_partner.png",
                "icon_hash": "0000000000000000",
                "relationship": Relationship.AUTHORIZED_PARTNER,
                "verification_method": VerificationMethod.STORE_LOOKUP,
                "is_verified": True,
                "trust_publisher": True,
                "is_active": True,
                "notes": "Partner demo iOS app",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": uuid4(),
                "brand_id": brand_id,
                "asset_type": AssetType.ANDROID_APP,
                "platform": "google_play",
                "stable_identifier": "com.kaveribank.android",
                "secondary_identifiers": {"package_name": "com.kaveribank.android"},
                "developer_id": "Kaveri Bank Ltd",
                "publisher_name": "Kaveri Bank Ltd",
                "display_name": "Kaveri Bank Mobile",
                "canonical_url": "https://play.google.com/store/apps/details?id=com.kaveribank.android",
                "icon_url": "https://assets.example.org/icons/kb_android.png",
                "icon_hash": "0000000000000000",
                "relationship": Relationship.OFFICIAL,
                "verification_method": VerificationMethod.STORE_LOOKUP,
                "is_verified": True,
                "trust_publisher": True,
                "is_active": True,
                "notes": "Official demo Android app",
                "created_at": now,
                "updated_at": now,
            },
        ]
        for a in demo_assets:
            self.assets[a["id"]] = a

    # --- Scan Operations ---

    def create_scan(
        self, brand_id: UUID, mode: ScanMode, options: ScanOptions
    ) -> ScanStartResponse:
        """Queue a scan run, enforcing one running scan per brand constraint."""
        if brand_id not in self.brands:
            if mode == ScanMode.DEMO or str(brand_id) == "acc79881-46b6-4938-8e2d-d10e5acbcb17":
                now = datetime.now(timezone.utc)
                self.brands[brand_id] = {
                    "id": brand_id,
                    "name": "Kaveri Bank",
                    "description": "Kaveri Bank Official",
                    "official_domains": ["kaveribank.com"],
                    "keywords": ["kaveri", "bank"],
                    "distinctive_tokens": ["kaveri"],
                    "generic_tokens_extra": [],
                    "industry_category": "Finance",
                    "demo_brand": True,
                    "created_at": now,
                    "updated_at": now,
                }
            else:
                raise NotFoundException(f"Brand '{brand_id}' not found.")

        if mode == ScanMode.DEMO:
            if not any(a["brand_id"] == brand_id for a in self.assets.values()):
                self._seed_demo_assets(brand_id)

        # Concurrency lock: one running scan per brand
        if brand_id in self.active_scans:
            existing_id = self.active_scans[brand_id]
            existing = self.scans.get(existing_id)
            if existing and existing["status"] in {ScanStatus.QUEUED, ScanStatus.RUNNING}:
                raise ScanAlreadyRunningException(
                    f"A scan is already running for brand '{brand_id}' (scan id: {existing_id})."
                )

        scan_id = uuid4()
        now = datetime.now(timezone.utc)
        record = {
            "id": scan_id,
            "brand_id": brand_id,
            "mode": mode,
            "status": ScanStatus.QUEUED,
            "stage": ScanStage.queued,
            "progress_percent": 0,
            "options": options,
            "source_outcomes": [],
            "funnel": ScanFunnel(),
            "findings_by_severity": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
            "events": [
                ScanEvent(
                    at=now,
                    stage="queued",
                    level="INFO",
                    message="Scan queued.",
                )
            ],
            "error_message": None,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
        }
        self.scans[scan_id] = record
        self.active_scans[brand_id] = scan_id
        self.findings_by_scan[scan_id] = []
        self.cleared_by_scan[scan_id] = []

        return ScanStartResponse(
            id=scan_id,
            brand_id=brand_id,
            mode=mode,
            status=ScanStatus.QUEUED,
            stage=ScanStage.queued,
            progress_percent=0,
            created_at=now,
        )

    def get_scan(self, scan_id: UUID) -> ScanDetailResponse:
        """Get scan detail and outcomes by scan ID."""
        record = self.scans.get(scan_id)
        if not record:
            raise NotFoundException(f"Scan '{scan_id}' not found.")
        return self._to_scan_detail_response(record)

    def list_scans_api(
        self, brand_id: UUID | None = None, limit: int = 20, offset: int = 0
    ) -> PaginatedResponse[ScanDetailResponse]:
        """List scan history ordered newest first."""
        all_scans = list(self.scans.values())
        if brand_id:
            all_scans = [s for s in all_scans if s["brand_id"] == brand_id]
        all_scans.sort(key=lambda s: s["created_at"], reverse=True)

        paged = all_scans[offset : offset + limit]
        items = [self._to_scan_detail_response(s) for s in paged]
        return PaginatedResponse[ScanDetailResponse](
            items=items,
            total=len(all_scans),
            limit=limit,
            offset=offset,
        )

    def update_scan_progress(
        self,
        scan_id: UUID,
        stage: ScanStage,
        progress: int,
        status: ScanStatus | None = None,
    ) -> None:
        """Update scan stage and progress percentage."""
        record = self.scans.get(scan_id)
        if record:
            record["stage"] = stage
            record["progress_percent"] = progress
            if status:
                record["status"] = status
            if stage == ScanStage.resolving_brand and not record["started_at"]:
                record["started_at"] = datetime.now(timezone.utc)

    def append_scan_event(self, scan_id: UUID, event: ScanEvent) -> None:
        """Append event to scan log (capped at 200)."""
        record = self.scans.get(scan_id)
        if record and len(record["events"]) < 200:
            record["events"].append(event)

    def save_scan_results(
        self,
        scan_id: UUID,
        status: ScanStatus,
        outcomes: list[SourceOutcome],
        funnel: ScanFunnel,
        findings_by_severity: dict[str, int],
        findings: list[FindingListItem],
        cleared: list[ClearedListItem],
        error_message: str | None = None,
    ) -> None:
        """Persist terminal scan outcomes, funnel math, findings and cleared items."""
        record = self.scans.get(scan_id)
        if not record:
            return

        now = datetime.now(timezone.utc)
        record["status"] = status
        record["stage"] = (
            ScanStage.completed if status != ScanStatus.FAILED else ScanStage.failed
        )
        record["progress_percent"] = 100
        record["source_outcomes"] = outcomes
        record["funnel"] = funnel
        record["findings_by_severity"] = findings_by_severity
        record["error_message"] = error_message
        record["completed_at"] = now

        for item in findings:
            cand_key = (
                item.candidate.platform.strip().lower(),
                item.candidate.stable_identifier.strip().lower(),
            )
            prior = self.candidate_memory.get(cand_key)
            if prior:
                item.status = prior["analyst_status"]
                item.changed_since_decision = prior.get("changed_since_decision", False)

            if item.id not in self.findings:
                self.findings[item.id] = self._create_finding_detail_from_list_item(item)
            else:
                existing = self.findings[item.id]
                existing.status = item.status
                existing.changed_since_decision = item.changed_since_decision

        self.findings_by_scan[scan_id] = findings
        self.cleared_by_scan[scan_id] = cleared

        # Release active scan lock
        b_id = record["brand_id"]
        if self.active_scans.get(b_id) == scan_id:
            del self.active_scans[b_id]

    def save_finding(self, detail: FindingDetailResponse) -> None:
        """Explicitly persist or update a complete FindingDetailResponse."""
        self.findings[detail.id] = detail
        # Keep candidate memory synchronized
        cand_key = (
            detail.candidate.platform.strip().lower(),
            detail.candidate.stable_identifier.strip().lower(),
        )
        self.candidate_memory[cand_key] = {
            "analyst_status": detail.status,
            "analyst_reason": detail.decision_history[-1].decision_reason if detail.decision_history else None,
            "notes": detail.decision_history[-1].notes if detail.decision_history else None,
            "last_decision_at": detail.decision_history[-1].created_at if detail.decision_history else None,
            "changed_since_decision": detail.changed_since_decision,
            "history": list(detail.decision_history),
        }

    def get_finding(self, finding_id: UUID) -> FindingDetailResponse:
        """Retrieve finding by ID or raise NotFoundException."""
        finding = self.findings.get(finding_id)
        if not finding:
            # Check findings_by_scan as fallback
            for scan_items in self.findings_by_scan.values():
                for item in scan_items:
                    if item.id == finding_id:
                        finding = self._create_finding_detail_from_list_item(item)
                        self.findings[finding_id] = finding
                        return finding
            raise NotFoundException(f"Finding '{finding_id}' not found.")
        return finding

    def list_findings(
        self,
        brand_id: UUID | None = None,
        scan_id: UUID | None = None,
        status: FindingStatus | None = None,
        asset_type: AssetType | None = None,
        platform: str | None = None,
        severity: Severity | None = None,
        min_score: int | None = None,
        source_mode: SourceMode | None = None,
        q: str | None = None,
        latest_only: bool = True,
        include_dismissed: bool = False,
        sort: str = "score_desc",
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResponse[FindingListItem]:
        """List findings matching documented filters, ordering, latest-only, and pagination."""
        all_findings: list[FindingDetailResponse | FindingListItem] = list(self.findings.values())
        for scan_items in self.findings_by_scan.values():
            for sf in scan_items:
                if not any(f.id == sf.id for f in all_findings):
                    all_findings.append(sf)

        filtered: list[FindingDetailResponse | FindingListItem] = []
        for f in all_findings:
            if brand_id and f.brand_id != brand_id:
                continue
            if scan_id and f.scan_id != scan_id:
                continue
            if status is not None:
                if f.status != status:
                    continue
            else:
                if not include_dismissed and f.status == FindingStatus.DISMISSED_FALSE_POSITIVE:
                    continue
            if asset_type and f.candidate.asset_type != asset_type:
                continue
            if platform and f.candidate.platform.strip().lower() != platform.strip().lower():
                continue
            if severity and f.severity != severity:
                continue
            if min_score is not None and f.risk_score < min_score:
                continue
            if source_mode and f.source_mode != source_mode:
                continue
            if q:
                term = q.strip().lower()
                c = f.candidate
                searchables = [
                    c.display_name or "",
                    c.publisher_name or "",
                    c.handle or "",
                    c.stable_identifier or "",
                ]
                if not any(term in s.lower() for s in searchables):
                    continue

            filtered.append(f)

        if latest_only:
            grouped: dict[tuple[str, str], list[FindingDetailResponse | FindingListItem]] = {}
            for item in filtered:
                k = (
                    item.candidate.platform.strip().lower(),
                    item.candidate.stable_identifier.strip().lower(),
                )
                grouped.setdefault(k, []).append(item)

            deduped: list[FindingDetailResponse | FindingListItem] = []
            for group in grouped.values():
                group.sort(
                    key=lambda x: getattr(x, "observed_at", None)
                    or getattr(x, "created_at", None)
                    or datetime.min.replace(tzinfo=timezone.utc),
                    reverse=True,
                )
                deduped.append(group[0])
            filtered = deduped

        # Ordering
        if sort == "score_asc":
            filtered.sort(key=lambda x: x.risk_score)
        elif sort == "seen_desc":
            filtered.sort(
                key=lambda x: getattr(x, "observed_at", None)
                or getattr(x, "created_at", None)
                or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
        elif sort == "name_asc":
            filtered.sort(key=lambda x: (x.candidate.display_name or "").lower())
        else:  # default: score_desc
            filtered.sort(key=lambda x: x.risk_score, reverse=True)

        paged = filtered[offset : offset + limit]
        items = [self._to_finding_list_item(f) for f in paged]
        return PaginatedResponse[FindingListItem](
            items=items,
            total=len(filtered),
            limit=limit,
            offset=offset,
        )

    async def record_decision(
        self,
        candidate_asset_id: UUID,
        assessment_id: UUID | None,
        previous_status: str,
        new_status: str,
        decision_reason: str,
        notes: str | None = None,
        actor_label: str = "analyst",
    ) -> FindingDetailResponse:
        """Record analyst decision through DecisionRepo protocol with decision memory and audit event."""
        target_id = assessment_id or candidate_asset_id
        finding = self.findings.get(target_id)
        if not finding:
            for s_findings in self.findings_by_scan.values():
                for sf in s_findings:
                    if sf.id == target_id:
                        finding = self._create_finding_detail_from_list_item(sf)
                        self.findings[target_id] = finding
                        break
                if finding:
                    break

        if not finding:
            raise NotFoundException(f"Finding '{target_id}' not found.")

        try:
            status_enum = FindingStatus(new_status)
        except ValueError:
            raise ValidationException(f"Invalid finding status '{new_status}'.")

        if status_enum in {
            FindingStatus.DISMISSED_FALSE_POSITIVE,
            FindingStatus.CONFIRMED_SUSPICIOUS,
        } and (not decision_reason or not decision_reason.strip()):
            raise ValidationException(
                f"decision_reason is required for status '{status_enum.value}'."
            )

        now = datetime.now(timezone.utc)
        prev_st = finding.status.value if hasattr(finding.status, "value") else str(finding.status)
        finding.status = status_enum

        history_item = DecisionHistoryItem(
            previous_status=prev_st,
            new_status=status_enum.value,
            decision_reason=decision_reason,
            notes=notes,
            actor_label=actor_label,
            created_at=now,
        )
        finding.decision_history.append(history_item)

        for scan_list in self.findings_by_scan.values():
            for item in scan_list:
                if item.id == finding.id:
                    item.status = status_enum

        cand_key = (
            finding.candidate.platform.strip().lower(),
            finding.candidate.stable_identifier.strip().lower(),
        )
        histories = list(self.candidate_memory.get(cand_key, {}).get("history", []))
        histories.append(history_item)
        self.candidate_memory[cand_key] = {
            "analyst_status": status_enum,
            "analyst_reason": decision_reason,
            "notes": notes,
            "last_decision_at": now,
            "changed_since_decision": False,
            "history": histories,
        }

        self.analyst_decisions.append({
            "id": uuid4(),
            "candidate_asset_id": candidate_asset_id,
            "assessment_id": assessment_id,
            "previous_status": prev_st,
            "new_status": status_enum.value,
            "decision_reason": decision_reason,
            "notes": notes,
            "actor_label": actor_label,
            "created_at": now,
        })

        self.record_audit_event(
            brand_id=finding.brand_id,
            actor_label=actor_label,
            event_type="FINDING_DECISION",
            entity_type="finding",
            entity_id=finding.id,
            details={
                "previous_status": prev_st,
                "new_status": status_enum.value,
                "decision_reason": decision_reason,
                "notes": notes,
            },
        )
        self.record_audit_event(
            brand_id=finding.brand_id,
            actor_label=actor_label,
            event_type="ANALYST_DECISION",
            entity_type="finding",
            entity_id=finding.id,
            details={
                "previous_status": prev_st,
                "new_status": status_enum.value,
                "decision_reason": decision_reason,
                "notes": notes,
            },
        )

        return finding

    def list_brand_cleared(
        self,
        brand_id: UUID,
        decision: IdentityDecision | None = None,
        scan_id: UUID | None = None,
        platform: str | None = None,
        q: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResponse[ClearedListItem]:
        """List cleared items for a brand with optional filtering and pagination."""
        if brand_id not in self.brands:
            raise NotFoundException(f"Brand '{brand_id}' not found.")

        brand_scans = [s for s in self.scans.values() if s["brand_id"] == brand_id]
        cleared_items: list[ClearedListItem] = []
        for s in brand_scans:
            if scan_id and s["id"] != scan_id:
                continue
            for item in self.cleared_by_scan.get(s["id"], []):
                if decision and item.decision != decision:
                    continue
                if platform and item.candidate.platform.strip().lower() != platform.strip().lower():
                    continue
                if q:
                    term = q.strip().lower()
                    c = item.candidate
                    searchables = [
                        c.display_name or "",
                        c.publisher_name or "",
                        c.stable_identifier or "",
                    ]
                    if not any(term in text.lower() for text in searchables):
                        continue
                cleared_items.append(item)

        paged = cleared_items[offset : offset + limit]
        return PaginatedResponse[ClearedListItem](
            items=paged,
            total=len(cleared_items),
            limit=limit,
            offset=offset,
        )

    def list_brand_audit(
        self,
        brand_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedResponse[AuditEventResponse]:
        """List audit trail events for a brand ordered newest first."""
        if brand_id not in self.brands:
            raise NotFoundException(f"Brand '{brand_id}' not found.")

        events = [e for e in self.audit_events if e["brand_id"] == brand_id]
        events.sort(key=lambda e: e["created_at"], reverse=True)

        paged = events[offset : offset + limit]
        items = [
            AuditEventResponse(
                id=e["id"],
                brand_id=e["brand_id"],
                actor_label=e["actor_label"],
                event_type=e["event_type"],
                entity_type=e["entity_type"],
                entity_id=e["entity_id"],
                details=e["details"],
                created_at=e["created_at"],
            )
            for e in paged
        ]
        return PaginatedResponse[AuditEventResponse](
            items=items,
            total=len(events),
            limit=limit,
            offset=offset,
        )

    def _create_finding_detail_from_list_item(
        self, item: FindingListItem
    ) -> FindingDetailResponse:
        """Construct full FindingDetailResponse from a FindingListItem."""
        cand_key = (
            item.candidate.platform.strip().lower(),
            item.candidate.stable_identifier.strip().lower(),
        )
        prior = self.candidate_memory.get(cand_key)
        history: list[DecisionHistoryItem] = []
        if prior and "history" in prior:
            history = list(prior["history"])

        signals = [
            SignalResult(
                signal=s.signal,
                group=EvidenceGroup.NAME if "name" in s.signal.lower() else EvidenceGroup.VISUAL,
                value=0.78,
                points=s.points,
                max_points=s.max_points,
                status=EvidenceStatus.OBSERVED,
                reason=s.reason,
                detail={"technique": item.technique.value, "similarity": 0.85},
            )
            for s in item.top_signals
        ]

        evidence_items = [
            EvidenceItem(
                id=uuid4(),
                evidence_type=(
                    "APP_STORE_METADATA"
                    if item.candidate.asset_type == AssetType.IOS_APP
                    else "SOCIAL_PROFILE_METADATA"
                ),
                source_id=(
                    "apple_itunes"
                    if item.candidate.platform == "apple_app_store"
                    else "bluesky_public"
                ),
                status=EvidenceStatus.OBSERVED,
                observed_at=item.observed_at,
                field_name="display_name",
                observed_value=item.candidate.display_name,
                source_url=item.candidate.canonical_url,
                notes="Observed via provider query.",
            )
        ]

        return FindingDetailResponse(
            id=item.id,
            brand_id=item.brand_id,
            scan_id=item.scan_id,
            candidate=FindingDetailCandidate(
                platform=item.candidate.platform,
                asset_type=item.candidate.asset_type,
                stable_identifier=item.candidate.stable_identifier,
                display_name=item.candidate.display_name,
                handle=item.candidate.handle,
                publisher_name=item.candidate.publisher_name,
                icon_url=item.candidate.icon_url,
                canonical_url=item.candidate.canonical_url,
                description=getattr(item.candidate, "description", None),
                category=getattr(item.candidate, "category", None),
                external_links=getattr(item.candidate, "external_links", []),
                created_at_source=getattr(item.candidate, "created_at_source", None),
                followers=getattr(item.candidate, "followers", None),
                rating_count=getattr(item.candidate, "rating_count", None),
            ),
            identity_guard=IdentityGuardResult(
                decision=IdentityDecision.CANDIDATE_FOR_REVIEW,
                rule="NO_EXACT_OR_PUBLISHER_MATCH",
                matched_official_asset_id=None,
                explanation="No registered identifier matches. Name similarity does not prove official status.",
            ),
            risk_score=item.risk_score,
            severity=item.severity,
            evidence_coverage=item.evidence_coverage,
            technique=item.technique,
            top_signals=item.top_signals,
            corroborating_groups=[
                EvidenceGroup.VISUAL,
                EvidenceGroup.CONTENT,
                EvidenceGroup.CONTEXT,
            ],
            gates_applied=[],
            score_breakdown=signals,
            evidence=evidence_items,
            explanation="Candidate for review: signals observed; not proof of malicious intent.",
            limitations=[
                "Hash similarity is not proof of copying.",
                "Description similarity is lexical, not semantic.",
            ],
            scoring_version="3.0.0",
            source_mode=item.source_mode,
            status=item.status,
            decision_history=history,
            created_at=item.observed_at,
            changed_since_decision=item.changed_since_decision,
        )

    def _to_finding_list_item(
        self, f: FindingDetailResponse | FindingListItem
    ) -> FindingListItem:
        if isinstance(f, FindingListItem):
            return f
        return FindingListItem(
            id=f.id,
            brand_id=f.brand_id,
            scan_id=f.scan_id,
            candidate=CandidateSummary(
                platform=f.candidate.platform,
                asset_type=f.candidate.asset_type,
                stable_identifier=f.candidate.stable_identifier,
                display_name=f.candidate.display_name,
                handle=f.candidate.handle,
                publisher_name=f.candidate.publisher_name,
                icon_url=f.candidate.icon_url,
                canonical_url=f.candidate.canonical_url,
            ),
            risk_score=f.risk_score,
            severity=f.severity,
            evidence_coverage=f.evidence_coverage,
            technique=f.technique,
            top_signals=f.top_signals,
            status=f.status,
            source_mode=f.source_mode,
            observed_at=f.created_at,
            changed_since_decision=f.changed_since_decision,
        )

    def get_scan_findings(
        self, scan_id: UUID, limit: int = 20, offset: int = 0
    ) -> PaginatedResponse[FindingListItem]:
        """Paginated list of findings surfaced in a scan."""
        if scan_id not in self.scans:
            raise NotFoundException(f"Scan '{scan_id}' not found.")
        findings = self.findings_by_scan.get(scan_id, [])
        paged = findings[offset : offset + limit]
        return PaginatedResponse[FindingListItem](
            items=paged,
            total=len(findings),
            limit=limit,
            offset=offset,
        )

    def get_scan_cleared(
        self, scan_id: UUID, limit: int = 20, offset: int = 0
    ) -> PaginatedResponse[ClearedListItem]:
        """Paginated list of cleared items from a scan."""
        if scan_id not in self.scans:
            raise NotFoundException(f"Scan '{scan_id}' not found.")
        cleared = self.cleared_by_scan.get(scan_id, [])
        paged = cleared[offset : offset + limit]
        return PaginatedResponse[ClearedListItem](
            items=paged,
            total=len(cleared),
            limit=limit,
            offset=offset,
        )

    def recover_running_scans(self) -> int:
        """Fail interrupted scans on server startup per Section 21."""
        recovered = 0
        now = datetime.now(timezone.utc)
        for s in self.scans.values():
            if s["status"] in {ScanStatus.RUNNING, ScanStatus.QUEUED}:
                s["status"] = ScanStatus.FAILED
                s["stage"] = ScanStage.failed
                s["error_message"] = "Interrupted by server restart"
                s["completed_at"] = now
                recovered += 1
        self.active_scans.clear()
        return recovered

    def _to_scan_detail_response(self, record: dict[str, Any]) -> ScanDetailResponse:
        return ScanDetailResponse(
            id=record["id"],
            brand_id=record["brand_id"],
            mode=record["mode"],
            status=record["status"],
            stage=record["stage"],
            progress_percent=record["progress_percent"],
            options=record["options"],
            source_outcomes=record["source_outcomes"],
            funnel=record["funnel"],
            findings_by_severity=record["findings_by_severity"],
            events=record["events"],
            error_message=record["error_message"],
            created_at=record["created_at"],
            started_at=record["started_at"],
            completed_at=record["completed_at"],
        )


memory_store = MemoryStore()


def get_memory_store() -> MemoryStore:
    """Dependency provider for storage double."""
    return memory_store
