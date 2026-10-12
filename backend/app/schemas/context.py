"""Context schemas for brand and registered official assets.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 7, 9, 11, 12
"""

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import AssetType, Relationship, VerificationMethod


class BrandCtx(BaseModel):
    """Context object representing brand configuration for scoring and query planning."""

    id: UUID
    name: str
    description: str | None = None
    official_domains: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    distinctive_tokens: list[str] = Field(default_factory=list)
    generic_tokens_extra: list[str] = Field(default_factory=list)
    industry_category: str | None = None
    demo_brand: bool = False


class OfficialAssetCtx(BaseModel):
    """Context object representing an official or partner asset for IdentityGuard."""

    id: UUID
    brand_id: UUID
    asset_type: AssetType
    platform: str
    stable_identifier: str
    secondary_identifiers: dict[str, str] = Field(default_factory=dict)
    developer_id: str | None = None
    publisher_name: str | None = None
    display_name: str
    handle: str | None = None
    description: str | None = None
    category: str | None = None
    canonical_url: str | None = None
    icon_url: str | None = None
    icon_hash: str | None = None
    relationship: Relationship = Relationship.OFFICIAL
    verification_method: VerificationMethod = VerificationMethod.STORE_LOOKUP
    is_verified: bool = False
    trust_publisher: bool = False
    is_active: bool = True
    notes: str | None = None
