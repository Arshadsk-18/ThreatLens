"""IdentityGuard specification and evaluation per Section 7 of ARCHITECTURE_API_CONTRACT.md.

Pure function, no network, no database.
Input: candidate, brand, active official assets.
Evaluate in order; the first match wins.

Rules:
1. R1_EXACT_ID:
   Same platform and (stable_identifier or secondary_identifiers such as bundle_id)
   equals an active, verified asset with relationship=OFFICIAL
   -> Decision: OFFICIAL_EXACT_MATCH
   Records matched asset ID.

2. R2_PUBLISHER_ID:
   Same platform and developer_id equals the developer_id of an active, verified
   OFFICIAL asset with trust_publisher=True
   -> Decision: OFFICIAL_PUBLISHER_MATCH
   Cleared.

3. R3_PARTNER:
   Same as R1 or R2 but against an asset with relationship=AUTHORIZED_PARTNER
   -> Decision: AUTHORIZED_PARTNER_MATCH

4. No match:
   Returns None (proceeds to relevance gate and scoring).

Strict Invariants:
- Never clear on name, publisher name string, logo, or description alone.
- Case-insensitive trimming of identifiers.
- Returns matched_official_asset_id, rule_id, and human-readable explanation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from backend.app.services.query_planner.models import (
    BrandCtx,
    IdentityDecision,
    OfficialAssetCtx,
    Relationship,
)


@dataclass(frozen=True)
class IdentityGuardResult:
    decision: IdentityDecision
    rule: str
    matched_official_asset_id: UUID
    explanation: str


class CandidateInput(BaseModel):
    platform: str
    stable_identifier: str
    secondary_identifiers: dict[str, str] = {}
    developer_id: str | None = None
    display_name: str
    publisher_name: str | None = None
    handle: str | None = None
    description: str | None = None
    icon_hash: str | None = None


def _clean_id(val: str | None) -> str:
    """Case-insensitive clean and trim of an identifier."""
    if not val:
        return ""
    return str(val).strip().lower()


def evaluate_identity_guard(
    candidate: CandidateInput | Any,
    brand: BrandCtx,
    official_assets: Sequence[OfficialAssetCtx],
) -> IdentityGuardResult | None:
    """Evaluate IdentityGuard rules in strict precedence:
    1. R1_EXACT_ID
    2. R2_PUBLISHER_ID
    3. R3_PARTNER
    4. None (no match)

    Strict invariant: Never clears on name, publisher name string, logo, or description alone.
    """
    cand_platform = _clean_id(getattr(candidate, "platform", ""))
    cand_stable_id = _clean_id(getattr(candidate, "stable_identifier", ""))
    cand_dev_id = _clean_id(getattr(candidate, "developer_id", None))

    cand_sec_ids: dict[str, str] = getattr(candidate, "secondary_identifiers", {}) or {}
    cand_sec_clean = {k.lower(): _clean_id(v) for k, v in cand_sec_ids.items() if v}

    # 1. Evaluate Rule R1_EXACT_ID:
    # Same platform and (stable_identifier or secondary_identifier) equals an active, verified asset with relationship=OFFICIAL
    for asset in official_assets:
        if not asset.is_active or not asset.is_verified:
            continue
        if asset.relationship != Relationship.OFFICIAL:
            continue
        if _clean_id(asset.platform) != cand_platform:
            continue

        asset_stable_id = _clean_id(asset.stable_identifier)
        asset_sec_clean = {k.lower(): _clean_id(v) for k, v in (asset.secondary_identifiers or {}).items() if v}

        # Check stable_identifier match
        if cand_stable_id and cand_stable_id == asset_stable_id:
            return IdentityGuardResult(
                decision=IdentityDecision.OFFICIAL_EXACT_MATCH,
                rule="R1_EXACT_ID",
                matched_official_asset_id=asset.id,
                explanation=f"Cleared: exact identifier match '{asset.stable_identifier}' with registered official asset '{asset.display_name}'.",
            )

        # Check secondary identifiers (e.g. bundle_id, handle)
        for key, val in cand_sec_clean.items():
            if not val:
                continue
            # Match against asset secondary_identifier with same key
            if asset_sec_clean.get(key) == val:
                return IdentityGuardResult(
                    decision=IdentityDecision.OFFICIAL_EXACT_MATCH,
                    rule="R1_EXACT_ID",
                    matched_official_asset_id=asset.id,
                    explanation=f"Cleared: exact {key} match '{val}' with registered official asset '{asset.display_name}'.",
                )
            # Or handle matching handle
            if key == "handle" and asset.handle and _clean_id(asset.handle) == val:
                return IdentityGuardResult(
                    decision=IdentityDecision.OFFICIAL_EXACT_MATCH,
                    rule="R1_EXACT_ID",
                    matched_official_asset_id=asset.id,
                    explanation=f"Cleared: exact handle match '{val}' with registered official asset '{asset.display_name}'.",
                )

        # Also check direct handle equality if present on candidate
        cand_handle = _clean_id(getattr(candidate, "handle", None))
        if cand_handle and asset.handle and cand_handle == _clean_id(asset.handle):
            return IdentityGuardResult(
                decision=IdentityDecision.OFFICIAL_EXACT_MATCH,
                rule="R1_EXACT_ID",
                matched_official_asset_id=asset.id,
                explanation=f"Cleared: exact handle match '{asset.handle}' with registered official asset '{asset.display_name}'.",
            )

    # 2. Evaluate Rule R2_PUBLISHER_ID:
    # Same platform and candidate developer_id matches developer_id of an active verified OFFICIAL asset with trust_publisher=True
    if cand_dev_id:
        for asset in official_assets:
            if not asset.is_active or not asset.is_verified:
                continue
            if asset.relationship != Relationship.OFFICIAL:
                continue
            if _clean_id(asset.platform) != cand_platform:
                continue
            if not asset.trust_publisher:
                continue

            asset_dev_id = _clean_id(asset.developer_id)
            if asset_dev_id and asset_dev_id == cand_dev_id:
                return IdentityGuardResult(
                    decision=IdentityDecision.OFFICIAL_PUBLISHER_MATCH,
                    rule="R2_PUBLISHER_ID",
                    matched_official_asset_id=asset.id,
                    explanation=f"Published by the registered developer '{asset.developer_id}'. Consider registering this app.",
                )

    # 3. Evaluate Rule R3_PARTNER:
    # Same as R1 or R2 but against an asset with relationship=AUTHORIZED_PARTNER
    for asset in official_assets:
        if not asset.is_active or not asset.is_verified:
            continue
        if asset.relationship != Relationship.AUTHORIZED_PARTNER:
            continue
        if _clean_id(asset.platform) != cand_platform:
            continue

        asset_stable_id = _clean_id(asset.stable_identifier)
        asset_sec_clean = {k.lower(): _clean_id(v) for k, v in (asset.secondary_identifiers or {}).items() if v}

        # Check exact ID match for partner
        if cand_stable_id and cand_stable_id == asset_stable_id:
            return IdentityGuardResult(
                decision=IdentityDecision.AUTHORIZED_PARTNER_MATCH,
                rule="R3_PARTNER",
                matched_official_asset_id=asset.id,
                explanation=f"Cleared: exact partner identifier match with registered authorized partner asset '{asset.display_name}'.",
            )

        for key, val in cand_sec_clean.items():
            if val and asset_sec_clean.get(key) == val:
                return IdentityGuardResult(
                    decision=IdentityDecision.AUTHORIZED_PARTNER_MATCH,
                    rule="R3_PARTNER",
                    matched_official_asset_id=asset.id,
                    explanation=f"Cleared: partner {key} match '{val}' with registered authorized partner '{asset.display_name}'.",
                )

        # Check developer_id match if trust_publisher is set for partner
        if cand_dev_id and asset.trust_publisher:
            asset_dev_id = _clean_id(asset.developer_id)
            if asset_dev_id and asset_dev_id == cand_dev_id:
                return IdentityGuardResult(
                    decision=IdentityDecision.AUTHORIZED_PARTNER_MATCH,
                    rule="R3_PARTNER",
                    matched_official_asset_id=asset.id,
                    explanation=f"Cleared: published by authorized partner developer ID '{asset.developer_id}'.",
                )

    # 4. No match: proceeds to relevance gate and scoring
    return None
