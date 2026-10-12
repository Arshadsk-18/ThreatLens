"""Official asset and prefill schemas for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.3
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.enums import (
    AssetType,
    ProviderErrorCode,
    Relationship,
    SourceMode,
    SourceStatus,
    VerificationMethod,
)


class AssetPrefillRequest(BaseModel):
    """Prefill request by store URL or platform identifier."""

    url: str | None = None
    platform: str | None = None
    identifier: str | None = None

    @model_validator(mode="after")
    def check_url_or_identifier(self) -> "AssetPrefillRequest":
        if not self.url and not (self.platform and self.identifier):
            raise ValueError(
                "Must provide either 'url' or both 'platform' and 'identifier'."
            )
        return self


class AssetPrefillDraft(BaseModel):
    """Draft asset returned by prefill for analyst review/editing before persistence."""

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
    verification_method: VerificationMethod = VerificationMethod.STORE_LOOKUP
    relationship: Relationship = Relationship.OFFICIAL
    trust_publisher: bool = True


class AssetPrefillResponse(BaseModel):
    """Response returned by POST /brands/{brand_id}/assets/prefill."""

    source_id: str
    source_mode: SourceMode | None = None
    retrieved_at: datetime | None = None
    draft: AssetPrefillDraft | None = None
    source_status: SourceStatus | None = None
    error_code: ProviderErrorCode | None = None
    message: str | None = None


class OfficialAssetCreate(BaseModel):
    """Payload for registering a new official or authorized partner asset."""

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
    relationship: Relationship = Relationship.OFFICIAL
    verification_method: VerificationMethod = VerificationMethod.STORE_LOOKUP
    is_verified: bool = False
    trust_publisher: bool = False
    notes: str | None = None


class OfficialAssetUpdate(BaseModel):
    """Payload for updating an official asset."""

    display_name: str | None = None
    handle: str | None = None
    description: str | None = None
    category: str | None = None
    canonical_url: str | None = None
    icon_url: str | None = None
    icon_hash: str | None = None
    developer_id: str | None = None
    publisher_name: str | None = None
    relationship: Relationship | None = None
    verification_method: VerificationMethod | None = None
    is_verified: bool | None = None
    trust_publisher: bool | None = None
    is_active: bool | None = None
    notes: str | None = None


class OfficialAssetResponse(BaseModel):
    """Registered official asset response."""

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
    relationship: Relationship
    verification_method: VerificationMethod
    is_verified: bool
    trust_publisher: bool
    is_active: bool
    notes: str | None = None
    warning: str | None = None
    created_at: datetime
    updated_at: datetime
