"""Scoring configuration and metadata definitions.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 6, 8, 11.1
"""

from typing import Any

from app.schemas.enums import AssetType

SCORING_VERSION = "3.0.0"

RELEVANCE_THRESHOLD = 0.60
REVIEW_THRESHOLD = 25

SEVERITY_BANDS: dict[str, list[int]] = {
    "LOW": [0, 24],
    "MEDIUM": [25, 49],
    "HIGH": [50, 74],
    "CRITICAL": [75, 100],
}

G2_MIN_CORROBORATING_GROUPS = 2
G3_MIN_EVIDENCE_COVERAGE = 0.50
G4_LOW_CONTENT_OVERLAP_THRESHOLD = 0.20

CATEGORY_SYNONYMS: dict[str, list[str]] = {
    "Finance": ["Finance", "Financial", "Banking", "Business"],
    "Banking": ["Finance", "Financial", "Banking"],
    "Shopping": ["Shopping", "E-Commerce", "Retail"],
    "Social": ["Social", "Social Networking"],
}

APP_SIGNALS: list[dict[str, Any]] = [
    {
        "signal_id": "name_lookalike",
        "group": "NAME",
        "max_points": 25.0,
        "description": "Normalized string similarity and distinctive-token weighting.",
    },
    {
        "signal_id": "publisher_impersonation",
        "group": "IDENTITY",
        "max_points": 20.0,
        "description": "Resemblance of candidate publisher name to official publisher or brand name.",
    },
    {
        "signal_id": "icon_similarity",
        "group": "VISUAL",
        "max_points": 20.0,
        "description": "Perceptual hash distance against registered official icon.",
    },
    {
        "signal_id": "description_similarity",
        "group": "CONTENT",
        "max_points": 15.0,
        "description": "TF-IDF char n-gram cosine similarity against official description.",
    },
    {
        "signal_id": "link_domain_mismatch",
        "group": "CONTEXT",
        "max_points": 8.0,
        "description": "External links pointing to unregistered third-party domains.",
    },
    {
        "signal_id": "lure_terms",
        "group": "CONTENT",
        "max_points": 6.0,
        "description": "Presence of high-risk lure terms in title or description.",
    },
    {
        "signal_id": "thin_footprint",
        "group": "CONTEXT",
        "max_points": 6.0,
        "description": "Recent release date or low rating count.",
    },
]

SOCIAL_SIGNALS: list[dict[str, Any]] = [
    {
        "signal_id": "name_lookalike",
        "group": "NAME",
        "max_points": 25.0,
        "description": "Similarity on display name and handle (higher of the two).",
    },
    {
        "signal_id": "avatar_similarity",
        "group": "VISUAL",
        "max_points": 20.0,
        "description": "Perceptual hash distance against official avatar.",
    },
    {
        "signal_id": "bio_similarity",
        "group": "CONTENT",
        "max_points": 15.0,
        "description": "TF-IDF cosine similarity of profile bio against brand descriptor text.",
    },
    {
        "signal_id": "link_domain_mismatch",
        "group": "CONTEXT",
        "max_points": 15.0,
        "description": "Bio external links pointing to non-official domains.",
    },
    {
        "signal_id": "lure_terms",
        "group": "CONTENT",
        "max_points": 10.0,
        "description": "Lure terms detected across bio, display name or handle.",
    },
    {
        "signal_id": "thin_footprint",
        "group": "CONTEXT",
        "max_points": 15.0,
        "description": "Account age, follower count, or post count below thresholds.",
    },
]

SIGNAL_TABLES: dict[str, list[dict[str, Any]]] = {
    "apps": APP_SIGNALS,
    "social": SOCIAL_SIGNALS,
}

SUPPORTED_PLATFORMS: list[dict[str, Any]] = [
    {
        "platform": "apple_app_store",
        "asset_type": AssetType.IOS_APP.value,
        "primary_identifier": "trackId",
        "secondary_identifiers": ["bundle_id"],
        "developer_id_field": "artistId",
        "live_source": "apple_itunes",
        "connected": True,
    },
    {
        "platform": "google_play",
        "asset_type": AssetType.ANDROID_APP.value,
        "primary_identifier": "package_name",
        "secondary_identifiers": [],
        "developer_id_field": "developer_id",
        "live_source": "google_play_snapshot",
        "connected": False,
    },
    {
        "platform": "bluesky",
        "asset_type": AssetType.SOCIAL_ACCOUNT.value,
        "primary_identifier": "did",
        "secondary_identifiers": ["handle"],
        "developer_id_field": None,
        "live_source": "bluesky_public",
        "connected": True,
    },
    {
        "platform": "instagram",
        "asset_type": AssetType.SOCIAL_ACCOUNT.value,
        "primary_identifier": "account_id_or_handle",
        "secondary_identifiers": ["handle"],
        "developer_id_field": None,
        "live_source": "instagram",
        "connected": False,
    },
    {
        "platform": "x",
        "asset_type": AssetType.SOCIAL_ACCOUNT.value,
        "primary_identifier": "account_id_or_handle",
        "secondary_identifiers": ["handle"],
        "developer_id_field": None,
        "live_source": "x",
        "connected": False,
    },
    {
        "platform": "facebook",
        "asset_type": AssetType.SOCIAL_ACCOUNT.value,
        "primary_identifier": "account_id_or_handle",
        "secondary_identifiers": ["handle"],
        "developer_id_field": None,
        "live_source": "facebook",
        "connected": False,
    },
]

SUPPORTED_ASSET_TYPES: list[str] = [
    AssetType.IOS_APP.value,
    AssetType.ANDROID_APP.value,
    AssetType.SOCIAL_ACCOUNT.value,
]
