"""Shared context models and types for ThreatLens v3 services.

Defines BrandCtx, OfficialAssetCtx, and QueryPlan schemas as specified in
Sections 5.4, 7, and 12 of ARCHITECTURE_API_CONTRACT.md.
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    IOS_APP = "IOS_APP"
    ANDROID_APP = "ANDROID_APP"
    SOCIAL_ACCOUNT = "SOCIAL_ACCOUNT"


class Relationship(str, Enum):
    OFFICIAL = "OFFICIAL"
    AUTHORIZED_PARTNER = "AUTHORIZED_PARTNER"


class VerificationMethod(str, Enum):
    OWNER_PROVIDED = "OWNER_PROVIDED"
    STORE_LOOKUP = "STORE_LOOKUP"
    DOMAIN_VERIFIED_HANDLE = "DOMAIN_VERIFIED_HANDLE"


class IdentityDecision(str, Enum):
    OFFICIAL_EXACT_MATCH = "OFFICIAL_EXACT_MATCH"
    OFFICIAL_PUBLISHER_MATCH = "OFFICIAL_PUBLISHER_MATCH"
    AUTHORIZED_PARTNER_MATCH = "AUTHORIZED_PARTNER_MATCH"
    BENIGN_LOOKALIKE = "BENIGN_LOOKALIKE"
    BELOW_THRESHOLD = "BELOW_THRESHOLD"
    CANDIDATE_FOR_REVIEW = "CANDIDATE_FOR_REVIEW"


class BrandCtx(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    official_domains: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    distinctive_tokens: list[str] = Field(default_factory=list)
    generic_tokens_extra: list[str] = Field(default_factory=list)
    industry_category: str | None = None
    demo_brand: bool = False


class OfficialAssetCtx(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    brand_id: UUID = Field(default_factory=uuid4)
    asset_type: AssetType
    platform: str
    stable_identifier: str
    secondary_identifiers: dict[str, str] = Field(default_factory=dict)
    developer_id: str | None = None
    publisher_name: str | None = None
    display_name: str
    handle: str | None = None
    description: str | None = None
    canonical_url: str = ""
    icon_url: str | None = None
    icon_hash: str | None = None
    relationship: Relationship = Relationship.OFFICIAL
    verification_method: VerificationMethod = VerificationMethod.STORE_LOOKUP
    is_verified: bool = True
    trust_publisher: bool = False
    is_active: bool = True
    notes: str = ""


class PlannedQuery(BaseModel):
    term: str
    kind: str  # BASE | SPACING | SEPARATOR | ADDED_WORD | DISTINCTIVE
    priority: int


class QueryPlan(BaseModel):
    brand_id: UUID
    queries: list[PlannedQuery]
