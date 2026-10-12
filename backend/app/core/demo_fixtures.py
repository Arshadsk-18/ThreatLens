"""Contract-compliant local demo fixtures loader for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 2, 5.3, 11.4, Appendix B
Owner: Person 2 (Orchestration & shared core)
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.candidate import NormalizedCandidate
from app.schemas.enums import AssetType, SourceMode

MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent / "db" / "seed" / "fixtures_manifest.json"
)


class FixtureUnavailableError(Exception):
    """Raised when demo fixture file or data is missing or corrupted."""


def load_demo_fixture_candidates(
    brand_name: str,
    industry_category: str | None = None,
    *,
    fail_simulation: bool = False,
) -> list[NormalizedCandidate]:
    """Load local demo fixture candidates for offline DEMO scans.

    Never makes external network calls.
    Returns simulated candidates covering all funnel stages:
    - Official exact match (R1)
    - Official publisher match (R2)
    - Benign namesake / unrelated category (G4)
    - Below threshold (<25)
    - Non-relevant candidate failing relevance gate (G1)
    - Suspicious lookalike candidate for review (Finding)
    """
    if fail_simulation:
        raise FixtureUnavailableError(
            "Demo fixture source is unavailable, corrupted, or missing."
        )

    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, encoding="utf-8") as f:
                data = json.load(f)
            fixtures = data.get("fixtures", [])
            if fixtures:
                candidates = []
                for item in fixtures:
                    cand_data = dict(item["candidate"])
                    cand_data["source_mode"] = SourceMode.SIMULATED
                    candidates.append(NormalizedCandidate(**cand_data))
                return candidates
        except Exception:
            pass

    now = datetime.now(timezone.utc)
    category = industry_category or "Finance"

    return [
        # 1. Official app cleared by exact identifier (R1)
        NormalizedCandidate(
            source_id="demo_fixtures",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="1234567890",
            secondary_identifiers={"bundle_id": "com.kaveribank.mobile"},
            display_name=brand_name,
            publisher_name="Kaveri Bank Ltd",
            developer_id="9000000001",
            category=category,
            canonical_url="https://apps.apple.com/in/app/kaveri-bank/id1234567890",
            icon_url="https://is1-ssl.mzstatic.com/image/thumb/app_icon.png",
            source_mode=SourceMode.SIMULATED,
            retrieved_at=now,
        ),
        # 2. Official Bluesky account (R1)
        NormalizedCandidate(
            source_id="demo_fixtures",
            platform="bluesky",
            asset_type=AssetType.SOCIAL_ACCOUNT,
            stable_identifier="did:plc:kaveriofficial123",
            handle="kaveribank.example",
            display_name=brand_name,
            publisher_name=None,
            developer_id=None,
            category=None,
            canonical_url="https://bsky.app/profile/kaveribank.example",
            icon_url="https://assets.example.org/avatars/kb_bsky.png",
            source_mode=SourceMode.SIMULATED,
            retrieved_at=now,
        ),
        # 3. Official second app published by registered developer (R2)
        NormalizedCandidate(
            source_id="demo_fixtures",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="9000000002",
            secondary_identifiers={"bundle_id": "com.kaveribank.corporate"},
            display_name=f"{brand_name} Corporate",
            publisher_name="Kaveri Bank Ltd",
            developer_id="9000000001",
            category=category,
            canonical_url="https://apps.apple.com/in/app/kaveri-bank-corporate/id9000000002",
            icon_url="https://is1-ssl.mzstatic.com/image/thumb/corporate_icon.png",
            source_mode=SourceMode.SIMULATED,
            retrieved_at=now,
        ),
        # 4. Authorized partner app (R3)
        NormalizedCandidate(
            source_id="demo_fixtures",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="1234567899",
            secondary_identifiers={"bundle_id": "com.kaveribank.partner"},
            display_name="Kaveri Merchant Connect",
            publisher_name="Kaveri Partner Solutions",
            developer_id="9000000099",
            category=category,
            canonical_url="https://apps.apple.com/in/app/kaveri-merchant/id1234567899",
            icon_url="https://assets.example.org/icons/kb_partner.png",
            source_mode=SourceMode.SIMULATED,
            retrieved_at=now,
        ),
        # 5. Official Android app (R1)
        NormalizedCandidate(
            source_id="demo_fixtures",
            platform="google_play",
            asset_type=AssetType.ANDROID_APP,
            stable_identifier="com.kaveribank.android",
            secondary_identifiers={"package_name": "com.kaveribank.android"},
            display_name=f"{brand_name} Mobile",
            publisher_name="Kaveri Bank Ltd",
            developer_id="Kaveri Bank Ltd",
            category=category,
            canonical_url="https://play.google.com/store/apps/details?id=com.kaveribank.android",
            icon_url="https://assets.example.org/icons/kb_android.png",
            source_mode=SourceMode.SIMULATED,
            retrieved_at=now,
        ),
        # 3. Benign namesake in unrelated category cleared by G4
        NormalizedCandidate(
            source_id="demo_fixtures",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="demo_benign_coffee",
            display_name=f"{brand_name} Coffee Roasters",
            publisher_name="Artisan Roasters LLP",
            developer_id="8000000055",
            category="Food & Drink",
            canonical_url="https://apps.apple.com/in/app/kaveri-coffee/id8888888888",
            source_mode=SourceMode.SIMULATED,
            retrieved_at=now,
        ),
        # 4. Low risk candidate below review threshold (< 25)
        NormalizedCandidate(
            source_id="demo_fixtures",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="demo_below_threshold_app",
            display_name=f"{brand_name} Community Forum",
            publisher_name="Independent Community",
            developer_id="7777777771",
            category=category,
            source_mode=SourceMode.SIMULATED,
            retrieved_at=now,
        ),
        # 5. Irrelevant result failing relevance gate G1
        NormalizedCandidate(
            source_id="demo_fixtures",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="demo_irrelevant_result",
            display_name="Completely Unrelated Utility Tool",
            publisher_name="Utility Softworks",
            developer_id="6666666661",
            category="Utilities",
            source_mode=SourceMode.SIMULATED,
            retrieved_at=now,
        ),
        # 6. Impersonation lookalike candidate for review (Finding)
        NormalizedCandidate(
            source_id="demo_fixtures",
            platform="apple_app_store",
            asset_type=AssetType.IOS_APP,
            stable_identifier="9876543210",
            display_name=f"{brand_name} Rewards",
            publisher_name="KB Rewards Studio",
            developer_id="9000000042",
            category=category,
            canonical_url="https://apps.apple.com/in/app/kaveri-rewards/id9876543210",
            icon_url="https://is1-ssl.mzstatic.com/image/thumb/rewards_icon.png",
            source_mode=SourceMode.SIMULATED,
            retrieved_at=now,
        ),
    ]
