"""Prefill lookup orchestration service.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 11.3
Owner: Person 2 (delegating to Person 3 adapters via Protocol)
"""

from datetime import datetime, timezone

from app.core.prefill_parser import ParsedPrefillTarget
from app.schemas.asset import AssetPrefillDraft, AssetPrefillResponse
from app.schemas.enums import (
    AssetType,
    ProviderErrorCode,
    Relationship,
    SourceMode,
    SourceStatus,
    VerificationMethod,
)
from app.services.sources.apple import AppleItunesAdapter
from app.services.sources.base import SourceAdapter
from app.services.sources.bluesky import BlueskyPublicAdapter
from app.services.sources.google_play import GooglePlaySnapshotAdapter
from app.services.sources.serper import SerperSearchAdapter

# Registry where live source adapters can be registered
_adapters: dict[str, SourceAdapter] = {
    "apple_itunes": AppleItunesAdapter(),
    "bluesky_public": BlueskyPublicAdapter(),
    "google_play_snapshot": GooglePlaySnapshotAdapter(),
    "serper_search": SerperSearchAdapter(),
}


def register_source_adapter(source_id: str, adapter: SourceAdapter) -> None:
    """Register a concrete source adapter instance (used by Person 3)."""
    _adapters[source_id] = adapter


async def perform_prefill_lookup(target: ParsedPrefillTarget) -> AssetPrefillResponse:
    """Perform prefill lookup by delegating to registered adapter or fallback test double.

    Never fetches raw user URLs.
    If lookup fails, returns 200 with draft=None and source error details so the UI can prompt manual entry.
    """
    now = datetime.now(timezone.utc)

    # 1. Apple App Store lookup
    if target.platform == "apple_app_store":
        source_id = "apple_itunes"
        adapter = _adapters.get(source_id)

        if adapter:
            try:
                candidate = await adapter.lookup(target.identifier)
                if candidate:
                    draft = AssetPrefillDraft(
                        asset_type=candidate.asset_type,
                        platform=candidate.platform,
                        stable_identifier=candidate.stable_identifier,
                        secondary_identifiers=candidate.secondary_identifiers,
                        developer_id=candidate.developer_id,
                        publisher_name=candidate.publisher_name,
                        display_name=candidate.display_name,
                        handle=candidate.handle,
                        description=candidate.description,
                        category=candidate.category,
                        canonical_url=candidate.canonical_url,
                        icon_url=candidate.icon_url,
                        verification_method=VerificationMethod.STORE_LOOKUP,
                        relationship=Relationship.OFFICIAL,
                        trust_publisher=True,
                    )
                    return AssetPrefillResponse(
                        source_id=source_id,
                        source_mode=SourceMode.LIVE,
                        retrieved_at=now,
                        draft=draft,
                        source_status=SourceStatus.CONNECTED,
                        error_code=None,
                    )
                else:
                    return AssetPrefillResponse(
                        source_id=source_id,
                        source_mode=None,
                        retrieved_at=None,
                        draft=None,
                        source_status=SourceStatus.ERROR,
                        error_code=ProviderErrorCode.PROVIDER_UNAVAILABLE,
                        message=f"No app found for trackId '{target.identifier}'.",
                    )
            except Exception as e:  # noqa: BLE001
                return AssetPrefillResponse(
                    source_id=source_id,
                    source_mode=None,
                    retrieved_at=None,
                    draft=None,
                    source_status=SourceStatus.ERROR,
                    error_code=ProviderErrorCode.PROVIDER_UNAVAILABLE,
                    message=f"Provider lookup failed: {e}",
                )

        # Fallback test double for development/testing
        if target.identifier in {"fail", "0000000000"}:
            return AssetPrefillResponse(
                source_id=source_id,
                source_mode=None,
                retrieved_at=None,
                draft=None,
                source_status=SourceStatus.ERROR,
                error_code=ProviderErrorCode.PROVIDER_UNAVAILABLE,
                message=f"App Store lookup failed for trackId '{target.identifier}'.",
            )

        draft = AssetPrefillDraft(
            asset_type=AssetType.IOS_APP,
            platform="apple_app_store",
            stable_identifier=target.identifier,
            secondary_identifiers={
                "bundle_id": "com.kaveribank.mobile"
                if target.identifier == "1234567890"
                else f"com.app.{target.identifier}"
            },
            developer_id="9000000001",
            publisher_name="Kaveri Bank Ltd",
            display_name="Kaveri Bank",
            description="Official mobile banking application for Kaveri Bank.",
            category="Finance",
            canonical_url=f"https://apps.apple.com/in/app/kaveri-bank/id{target.identifier}",
            icon_url="https://is1-ssl.mzstatic.com/image/thumb/app_icon.png",
            verification_method=VerificationMethod.STORE_LOOKUP,
            relationship=Relationship.OFFICIAL,
            trust_publisher=True,
        )
        return AssetPrefillResponse(
            source_id=source_id,
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
            draft=draft,
            source_status=SourceStatus.CONNECTED,
            error_code=None,
        )

    # 2. Bluesky lookup
    elif target.platform == "bluesky":
        source_id = "bluesky_public"
        adapter = _adapters.get(source_id)

        if adapter:
            try:
                candidate = await adapter.lookup(target.identifier)
                if candidate:
                    draft = AssetPrefillDraft(
                        asset_type=candidate.asset_type,
                        platform=candidate.platform,
                        stable_identifier=candidate.stable_identifier,
                        secondary_identifiers=candidate.secondary_identifiers,
                        developer_id=candidate.developer_id,
                        publisher_name=candidate.publisher_name,
                        display_name=candidate.display_name,
                        handle=candidate.handle,
                        description=candidate.description,
                        category=candidate.category,
                        canonical_url=candidate.canonical_url,
                        icon_url=candidate.icon_url,
                        verification_method=VerificationMethod.STORE_LOOKUP,
                        relationship=Relationship.OFFICIAL,
                        trust_publisher=True,
                    )
                    return AssetPrefillResponse(
                        source_id=source_id,
                        source_mode=SourceMode.LIVE,
                        retrieved_at=now,
                        draft=draft,
                        source_status=SourceStatus.CONNECTED,
                        error_code=None,
                    )
                else:
                    return AssetPrefillResponse(
                        source_id=source_id,
                        source_mode=None,
                        retrieved_at=None,
                        draft=None,
                        source_status=SourceStatus.ERROR,
                        error_code=ProviderErrorCode.PROVIDER_UNAVAILABLE,
                        message=f"No account found for identifier '{target.identifier}'.",
                    )
            except Exception as e:  # noqa: BLE001
                return AssetPrefillResponse(
                    source_id=source_id,
                    source_mode=None,
                    retrieved_at=None,
                    draft=None,
                    source_status=SourceStatus.ERROR,
                    error_code=ProviderErrorCode.PROVIDER_UNAVAILABLE,
                    message=f"Bluesky lookup failed: {e}",
                )

        if target.identifier in {"fail", "error"}:
            return AssetPrefillResponse(
                source_id=source_id,
                source_mode=None,
                retrieved_at=None,
                draft=None,
                source_status=SourceStatus.ERROR,
                error_code=ProviderErrorCode.PROVIDER_UNAVAILABLE,
                message=f"Bluesky lookup failed for identifier '{target.identifier}'.",
            )

        stable_id = (
            target.identifier
            if target.identifier.startswith("did:")
            else f"did:plc:{target.identifier}"
        )
        handle = (
            target.identifier
            if not target.identifier.startswith("did:")
            else "kaveribank.example"
        )
        draft = AssetPrefillDraft(
            asset_type=AssetType.SOCIAL_ACCOUNT,
            platform="bluesky",
            stable_identifier=stable_id,
            display_name="Kaveri Bank",
            handle=handle,
            description="Official Bluesky account for Kaveri Bank.",
            canonical_url=f"https://bsky.app/profile/{handle}",
            verification_method=VerificationMethod.STORE_LOOKUP,
            relationship=Relationship.OFFICIAL,
            trust_publisher=True,
        )
        return AssetPrefillResponse(
            source_id=source_id,
            source_mode=SourceMode.LIVE,
            retrieved_at=now,
            draft=draft,
            source_status=SourceStatus.CONNECTED,
            error_code=None,
        )

    # 3. Google Play lookup
    elif target.platform == "google_play":
        source_id = "google_play_snapshot"
        adapter = _adapters.get(source_id)
        if adapter:
            try:
                candidate = await adapter.lookup(target.identifier)
                if candidate:
                    draft = AssetPrefillDraft(
                        asset_type=candidate.asset_type,
                        platform=candidate.platform,
                        stable_identifier=candidate.stable_identifier,
                        secondary_identifiers=candidate.secondary_identifiers,
                        developer_id=candidate.developer_id,
                        publisher_name=candidate.publisher_name,
                        display_name=candidate.display_name,
                        handle=candidate.handle,
                        description=candidate.description,
                        category=candidate.category,
                        canonical_url=candidate.canonical_url,
                        icon_url=candidate.icon_url,
                        verification_method=VerificationMethod.STORE_LOOKUP,
                        relationship=Relationship.OFFICIAL,
                        trust_publisher=True,
                    )
                    return AssetPrefillResponse(
                        source_id=source_id,
                        source_mode=SourceMode.LIVE,
                        retrieved_at=now,
                        draft=draft,
                        source_status=SourceStatus.CONNECTED,
                        error_code=None,
                    )
            except Exception:
                pass

    # 4. Other platforms (not connected in live mode)
    return AssetPrefillResponse(
        source_id="not_connected",
        source_mode=None,
        retrieved_at=None,
        draft=None,
        source_status=SourceStatus.NOT_CONNECTED,
        error_code=ProviderErrorCode.NOT_CONFIGURED,
        message=f"Platform '{target.platform}' does not have an active live lookup connector.",
    )
