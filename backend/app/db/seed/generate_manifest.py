"""Generator script for Kaveri Bank demo fixtures manifest (Appendix B)."""

import json
from pathlib import Path

NOW_ISO = "2026-10-12T05:30:20Z"
PAST_ISO = "2026-10-10T12:00:00Z"

fixtures = []

# ==============================================================================
# 1. IDENTITY CLEARED (5 candidates)
# ==============================================================================

# 1.1 Exact Official iOS App (R1_EXACT_ID)
fixtures.append(
    {
        "id": "c-0001",
        "intended_label": "cleared_r1",
        "asset_type": "IOS_APP",
        "platform": "apple_app_store",
        "source_mode": "CACHED",
        "candidate": {
            "source_id": "apple_itunes",
            "platform": "apple_app_store",
            "asset_type": "IOS_APP",
            "stable_identifier": "1234567890",
            "secondary_identifiers": {"bundle_id": "com.kaveribank.mobile"},
            "display_name": "Kaveri Bank",
            "handle": None,
            "publisher_name": "Kaveri Bank Ltd",
            "developer_id": "9000000001",
            "description": "Official mobile banking application of Kaveri Bank.",
            "category": "Finance",
            "external_links": ["https://kaveribank.example"],
            "icon_url": "https://assets.example.org/icons/kb_official.png",
            "icon_hash": "0000000000000000",
            "canonical_url": "https://apps.apple.com/in/app/kaveri-bank/id1234567890",
            "created_at_source": "2020-01-15T00:00:00Z",
            "followers": None,
            "following": None,
            "posts_count": None,
            "rating_count": 45000,
            "source_mode": "CACHED",
            "retrieved_at": PAST_ISO,
            "matched_queries": ["kaveri bank"],
        },
    }
)

# 1.2 Exact Official Bluesky Account (R1_EXACT_ID)
fixtures.append(
    {
        "id": "c-0002",
        "intended_label": "cleared_r1",
        "asset_type": "SOCIAL_ACCOUNT",
        "platform": "bluesky",
        "source_mode": "CACHED",
        "candidate": {
            "source_id": "bluesky_public",
            "platform": "bluesky",
            "asset_type": "SOCIAL_ACCOUNT",
            "stable_identifier": "did:plc:kaveriofficial123",
            "secondary_identifiers": {},
            "display_name": "Kaveri Bank",
            "handle": "kaveribank.example",
            "publisher_name": None,
            "developer_id": None,
            "description": "Official Bluesky handle for Kaveri Bank. Updates and support.",
            "category": None,
            "external_links": ["https://kaveribank.example"],
            "icon_url": "https://assets.example.org/avatars/kb_bsky.png",
            "icon_hash": "0000000000000000",
            "canonical_url": "https://bsky.app/profile/kaveribank.example",
            "created_at_source": "2023-05-10T00:00:00Z",
            "followers": 15000,
            "following": 12,
            "posts_count": 850,
            "rating_count": None,
            "source_mode": "CACHED",
            "retrieved_at": PAST_ISO,
            "matched_queries": ["kaveri bank"],
        },
    }
)

# 1.3 Second App by Registered Developer ID (R2_PUBLISHER_ID)
fixtures.append(
    {
        "id": "c-0003",
        "intended_label": "cleared_r2",
        "asset_type": "IOS_APP",
        "platform": "apple_app_store",
        "source_mode": "CACHED",
        "candidate": {
            "source_id": "apple_itunes",
            "platform": "apple_app_store",
            "asset_type": "IOS_APP",
            "stable_identifier": "1234567891",
            "secondary_identifiers": {"bundle_id": "com.kaveribank.wealth"},
            "display_name": "Kaveri Wealth Management",
            "handle": None,
            "publisher_name": "Kaveri Bank Ltd",
            "developer_id": "9000000001",
            "description": "Portfolio and wealth management services by Kaveri Bank.",
            "category": "Finance",
            "external_links": ["https://kaveribank.example/wealth"],
            "icon_url": "https://assets.example.org/icons/kb_wealth.png",
            "icon_hash": "0000000000000000",
            "canonical_url": "https://apps.apple.com/in/app/kaveri-wealth/id1234567891",
            "created_at_source": "2022-03-01T00:00:00Z",
            "followers": None,
            "following": None,
            "posts_count": None,
            "rating_count": 3200,
            "source_mode": "CACHED",
            "retrieved_at": PAST_ISO,
            "matched_queries": ["kaveri"],
        },
    }
)

# 1.4 Authorized Partner Asset (R3_PARTNER)
fixtures.append(
    {
        "id": "c-0004",
        "intended_label": "cleared_r3",
        "asset_type": "IOS_APP",
        "platform": "apple_app_store",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "apple_app_store",
            "asset_type": "IOS_APP",
            "stable_identifier": "1234567899",
            "secondary_identifiers": {"bundle_id": "com.kaveribank.partner"},
            "display_name": "Kaveri Merchant Connect",
            "handle": None,
            "publisher_name": "Kaveri Partner Solutions",
            "developer_id": "9000000099",
            "description": "Authorized partner portal for Kaveri Bank merchant settlement.",
            "category": "Finance",
            "external_links": ["https://partner.kaveribank.example"],
            "icon_url": "https://assets.example.org/icons/kb_partner.png",
            "icon_hash": "0000000000000000",
            "canonical_url": "https://apps.apple.com/in/app/kaveri-merchant/id1234567899",
            "created_at_source": "2023-01-10T00:00:00Z",
            "followers": None,
            "following": None,
            "posts_count": None,
            "rating_count": 890,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaveri bank"],
        },
    }
)

# 1.5 Official Android App (R1_EXACT_ID / SIMULATED)
fixtures.append(
    {
        "id": "c-0005",
        "intended_label": "cleared_r1",
        "asset_type": "ANDROID_APP",
        "platform": "google_play",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "google_play",
            "asset_type": "ANDROID_APP",
            "stable_identifier": "com.kaveribank.android",
            "secondary_identifiers": {"package_name": "com.kaveribank.android"},
            "display_name": "Kaveri Bank Mobile",
            "handle": None,
            "publisher_name": "Kaveri Bank Ltd",
            "developer_id": "Kaveri Bank Ltd",
            "description": "Official Android app for Kaveri Bank customers.",
            "category": "Finance",
            "external_links": ["https://kaveribank.example"],
            "icon_url": "https://assets.example.org/icons/kb_android.png",
            "icon_hash": "0000000000000000",
            "canonical_url": "https://play.google.com/store/apps/details?id=com.kaveribank.android",
            "created_at_source": "2020-02-20T00:00:00Z",
            "followers": None,
            "following": None,
            "posts_count": None,
            "rating_count": 120000,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaveri bank"],
        },
    }
)

# ==============================================================================
# 2. BENIGN LOOKALIKES (14 candidates: G4 / G5)
# ==============================================================================

# 2.1 Declared Fan Page (Scenario B - G5_DECLARED_UNOFFICIAL)
fixtures.append(
    {
        "id": "c-0006",
        "intended_label": "benign_g5",
        "asset_type": "SOCIAL_ACCOUNT",
        "platform": "bluesky",
        "source_mode": "CACHED",
        "candidate": {
            "source_id": "bluesky_public",
            "platform": "bluesky",
            "asset_type": "SOCIAL_ACCOUNT",
            "stable_identifier": "did:plc:kaverifanshonest01",
            "secondary_identifiers": {},
            "display_name": "Kaveri Bank Fans",
            "handle": "kaverifans.bsky.social",
            "publisher_name": None,
            "developer_id": None,
            "description": "Unofficial fan page, not affiliated. Community discussions about regional banking history.",
            "category": None,
            "external_links": [],
            "icon_url": "https://assets.example.org/avatars/fan_honest.png",
            "icon_hash": "000000001f7f7fff",  # 0.55 similarity (non-copy)
            "canonical_url": "https://bsky.app/profile/kaverifans.bsky.social",
            "created_at_source": "2024-06-01T00:00:00Z",
            "followers": 2300,
            "following": 150,
            "posts_count": 900,
            "rating_count": None,
            "source_mode": "CACHED",
            "retrieved_at": PAST_ISO,
            "matched_queries": ["kaveri bank fans"],
        },
    }
)

# 2.2 Fan Page that quotes brand text (Scenario C - G5_DECLARED_UNOFFICIAL)
fixtures.append(
    {
        "id": "c-0007",
        "intended_label": "benign_g5",
        "asset_type": "SOCIAL_ACCOUNT",
        "platform": "bluesky",
        "source_mode": "CACHED",
        "candidate": {
            "source_id": "bluesky_public",
            "platform": "bluesky",
            "asset_type": "SOCIAL_ACCOUNT",
            "stable_identifier": "did:plc:kaverifansquotes02",
            "secondary_identifiers": {},
            "display_name": "Kaveri Bank Enthusiasts",
            "handle": "kaveriquotes.bsky.social",
            "publisher_name": None,
            "developer_id": None,
            "description": "Unofficial fan page, not affiliated. Devoted to Kaveri Bank customer experiences and legacy.",
            "category": None,
            "external_links": [],
            "icon_url": "https://assets.example.org/avatars/fan_quotes.png",
            "icon_hash": "000000001f7f7fff",  # 0.55 similarity
            "canonical_url": "https://bsky.app/profile/kaveriquotes.bsky.social",
            "created_at_source": "2024-05-15T00:00:00Z",
            "followers": 1800,
            "following": 80,
            "posts_count": 420,
            "rating_count": None,
            "source_mode": "CACHED",
            "retrieved_at": PAST_ISO,
            "matched_queries": ["kaveri bank"],
        },
    }
)

# 2.3 - 2.8 Six Unrelated Category Apps (G4_UNRELATED_CATEGORY)
unrelated_apps = [
    (
        "c-0008",
        "Kaveri Coffee Roasters",
        "Food & Drink",
        "Artisan filter coffee and beans delivered across Karnataka.",
        "1000000001",
        "Coffee Roasters Ltd",
    ),
    (
        "c-0009",
        "Kaveri Silk & Sarees",
        "Shopping",
        "Traditional pure Mysore silk sarees catalog and store locator.",
        "1000000002",
        "Kaveri Handlooms",
    ),
    (
        "c-0010",
        "Kaveri Travel Guides",
        "Travel",
        "Offline audio guides and trail maps for Kaveri basin historical sites.",
        "1000000003",
        "Heritage Trails",
    ),
    (
        "c-0011",
        "Kaveri Water Purifiers",
        "Utilities",
        "IoT companion app for residential smart water purifier filters.",
        "1000000004",
        "Kaveri CleanTech",
    ),
    (
        "c-0012",
        "Kaveri Real Estate",
        "Business",
        "Residential and agricultural land plots in Mysore and Bangalore.",
        "1000000005",
        "Kaveri Properties",
    ),
    (
        "c-0013",
        "Kaveri Music Player",
        "Music",
        "Offline music player with audio equalization and playlist management.",
        "1000000006",
        "Deccan Beats",
    ),
]

for cid, name, cat, desc, dev_id, pub in unrelated_apps:
    fixtures.append(
        {
            "id": cid,
            "intended_label": "benign_g4",
            "asset_type": "IOS_APP",
            "platform": "apple_app_store",
            "source_mode": "CACHED",
            "candidate": {
                "source_id": "apple_itunes",
                "platform": "apple_app_store",
                "asset_type": "IOS_APP",
                "stable_identifier": f"980000{cid[-2:]}",
                "secondary_identifiers": {
                    "bundle_id": f"com.kaveri.{cat.lower().replace(' ', '')}"
                },
                "display_name": name,
                "handle": None,
                "publisher_name": pub,
                "developer_id": dev_id,
                "description": desc,
                "category": cat,
                "external_links": [
                    f"https://{cat.lower().replace(' ', '')}.example.org"
                ],
                "icon_url": f"https://assets.example.org/icons/{cid}.png",
                "icon_hash": "000000001f7f7fff",  # 0.55 similarity
                "canonical_url": f"https://apps.apple.com/app/id980000{cid[-2:]}",
                "created_at_source": "2021-08-10T00:00:00Z",
                "followers": None,
                "following": None,
                "posts_count": None,
                "rating_count": 450,
                "source_mode": "CACHED",
                "retrieved_at": PAST_ISO,
                "matched_queries": ["kaveri"],
            },
        }
    )

# 2.9 - 2.14 Six Unrelated Social Pages (G4_LOW_CONTENT_OVERLAP)
unrelated_social = [
    (
        "c-0014",
        "Kaveri Wildlife Sanctuary",
        "bluesky",
        "Conservation updates, flora and fauna photography from sanctuary rangers.",
        "did:plc:kaveriws001",
    ),
    (
        "c-0015",
        "Kaveri Literary Society",
        "bluesky",
        "Monthly book reviews, Kannada poetry readings and cultural archives.",
        "did:plc:kaverilit002",
    ),
    (
        "c-0016",
        "Kaveri Photography Club",
        "instagram",
        "Weekly landscape photography contests along river tributaries.",
        "kaveri_photo_club",
    ),
    (
        "c-0017",
        "Kaveri River Conservation",
        "x",
        "Citizen volunteers monitoring river water purity and tree plantation drives.",
        "kaveri_clean",
    ),
    (
        "c-0018",
        "Kaveri Youth Sports Club",
        "facebook",
        "Local grassroots football, cricket tournaments and fitness camps.",
        "kaveri_sports",
    ),
    (
        "c-0019",
        "Kaveri Classical Dance Academy",
        "bluesky",
        "Bharatanatyam training workshops and seasonal performance schedules.",
        "did:plc:kaveridance003",
    ),
]

for cid, name, plat, desc, handle in unrelated_social:
    fixtures.append(
        {
            "id": cid,
            "intended_label": "benign_g4",
            "asset_type": "SOCIAL_ACCOUNT",
            "platform": plat,
            "source_mode": "SIMULATED",
            "candidate": {
                "source_id": "demo_fixtures",
                "platform": plat,
                "asset_type": "SOCIAL_ACCOUNT",
                "stable_identifier": handle if ":" in handle else f"handle:{handle}",
                "secondary_identifiers": {},
                "display_name": name,
                "handle": handle,
                "publisher_name": None,
                "developer_id": None,
                "description": desc,
                "category": None,
                "external_links": [],
                "icon_url": f"https://assets.example.org/avatars/{cid}.png",
                "icon_hash": "000000001f7f7fff",  # 0.55 similarity
                "canonical_url": f"https://{plat}.example.com/{handle}",
                "created_at_source": "2022-04-12T00:00:00Z",
                "followers": 1200,
                "following": 140,
                "posts_count": 310,
                "rating_count": None,
                "source_mode": "SIMULATED",
                "retrieved_at": NOW_ISO,
                "matched_queries": ["kaveri"],
            },
        }
    )

# ==============================================================================
# 3. IMPERSONATION CANDIDATES (12 candidates covering all techniques & scenarios)
# ==============================================================================

# 3.1 Walkthrough Scenario A: Fake App "Kaveri Bank Rewards" (ADDED_WORD, HIGH ~72)
fixtures.append(
    {
        "id": "c-0020",
        "intended_label": "impersonation_added_word",
        "asset_type": "IOS_APP",
        "platform": "apple_app_store",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "apple_app_store",
            "asset_type": "IOS_APP",
            "stable_identifier": "9876543210",
            "secondary_identifiers": {"bundle_id": "com.kaveribank.rewards"},
            "display_name": "Kaveri Bank Rewards",
            "handle": None,
            "publisher_name": "KB Rewards Studio",
            "developer_id": "9000000042",
            "description": "Official Kaveri Bank rewards catalog. Login to claim cashback, instant loan and redeem credit card points.",
            "category": "Finance",
            "external_links": ["https://kb-rewards.example"],
            "icon_url": "https://assets.example.org/icons/kb_fake_rewards.png",
            "icon_hash": "000000000000000f",  # 0.93 similarity (copied icon)
            "canonical_url": "https://apps.apple.com/app/id9876543210",
            "created_at_source": "2026-09-21T00:00:00Z",  # released 21 days ago
            "followers": None,
            "following": None,
            "posts_count": None,
            "rating_count": 12,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaveri bank rewards"],
        },
    }
)

# 3.2 Homoglyph Cyrillic U+0456: "Kaverі Bank" (HOMOGLYPH)
fixtures.append(
    {
        "id": "c-0021",
        "intended_label": "impersonation_homoglyph",
        "asset_type": "IOS_APP",
        "platform": "apple_app_store",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "apple_app_store",
            "asset_type": "IOS_APP",
            "stable_identifier": "9876543211",
            "secondary_identifiers": {"bundle_id": "com.homoglyph.kaveribank"},
            "display_name": "Kaver\u0456 Bank",  # Cyrillic small letter byelorussian-ukrainian i
            "handle": None,
            "publisher_name": "Kaver\u0456 Mobile Tech",
            "developer_id": "9000000077",
            "description": "Fast banking and secure payment transfers for Kaveri account holders.",
            "category": "Finance",
            "external_links": ["https://kaveri-fastpay.example"],
            "icon_url": "https://assets.example.org/icons/homoglyph.png",
            "icon_hash": "000000000000000f",
            "canonical_url": "https://apps.apple.com/app/id9876543211",
            "created_at_source": "2026-09-10T00:00:00Z",
            "followers": None,
            "following": None,
            "posts_count": None,
            "rating_count": 5,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaveri bank"],
        },
    }
)

# 3.3 Character Swap: "KaveriBnak" (CHARACTER_SWAP)
fixtures.append(
    {
        "id": "c-0022",
        "intended_label": "impersonation_character_swap",
        "asset_type": "ANDROID_APP",
        "platform": "google_play",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "google_play",
            "asset_type": "ANDROID_APP",
            "stable_identifier": "com.kaveribnak.app",
            "secondary_identifiers": {},
            "display_name": "KaveriBnak Mobile",
            "handle": None,
            "publisher_name": "KaveriBnak Devs",
            "developer_id": "dev_swap_01",
            "description": "Secure online banking login for KaveriBnak retail clients. Verify KYC and claim instant loan.",
            "category": "Finance",
            "external_links": ["https://kaveribnak-secure.example"],
            "icon_url": "https://assets.example.org/icons/swap.png",
            "icon_hash": "000000000000000f",
            "canonical_url": "https://play.google.com/store/apps/details?id=com.kaveribnak.app",
            "created_at_source": "2026-09-01T00:00:00Z",
            "followers": None,
            "following": None,
            "posts_count": None,
            "rating_count": 18,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaveribnak"],
        },
    }
)

# 3.4 Omission: "Kaver Bank" (OMISSION)
fixtures.append(
    {
        "id": "c-0023",
        "intended_label": "impersonation_omission",
        "asset_type": "IOS_APP",
        "platform": "apple_app_store",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "apple_app_store",
            "asset_type": "IOS_APP",
            "stable_identifier": "9876543213",
            "secondary_identifiers": {"bundle_id": "com.kaver.bank"},
            "display_name": "Kaver Bank",
            "handle": None,
            "publisher_name": "Kaver Digital Corp",
            "developer_id": "9000000088",
            "description": "Mobile banking login and quick fund transfers for Kaver Bank.",
            "category": "Finance",
            "external_links": ["https://kaver-bank.example"],
            "icon_url": "https://assets.example.org/icons/omission.png",
            "icon_hash": "000000000000000f",
            "canonical_url": "https://apps.apple.com/app/id9876543213",
            "created_at_source": "2026-08-20T00:00:00Z",
            "followers": None,
            "following": None,
            "posts_count": None,
            "rating_count": 30,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaver bank"],
        },
    }
)

# 3.5 Spacing: "Kaveri  Bank" (SPACING)
fixtures.append(
    {
        "id": "c-0024",
        "intended_label": "impersonation_spacing",
        "asset_type": "SOCIAL_ACCOUNT",
        "platform": "bluesky",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "bluesky",
            "asset_type": "SOCIAL_ACCOUNT",
            "stable_identifier": "did:plc:kaverispacing99",
            "secondary_identifiers": {},
            "display_name": "Kaveri  Bank",  # double space
            "handle": "kaveri-bank.bsky.social",
            "publisher_name": None,
            "developer_id": None,
            "description": "Official Kaveri  Bank helpdesk. Send message for instant loan approval and account verification.",
            "category": None,
            "external_links": ["https://short.example/kb-help"],
            "icon_url": "https://assets.example.org/avatars/spacing.png",
            "icon_hash": "0000000000000007",
            "canonical_url": "https://bsky.app/profile/kaveri-bank.bsky.social",
            "created_at_source": "2026-09-28T00:00:00Z",
            "followers": 45,
            "following": 5,
            "posts_count": 8,
            "rating_count": None,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaveri  bank"],
        },
    }
)

# 3.6 Separator: "Kaveri-Bank-Online" (SEPARATOR)
fixtures.append(
    {
        "id": "c-0025",
        "intended_label": "impersonation_separator",
        "asset_type": "SOCIAL_ACCOUNT",
        "platform": "x",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "x",
            "asset_type": "SOCIAL_ACCOUNT",
            "stable_identifier": "handle:Kaveri_Bank_Online",
            "secondary_identifiers": {},
            "display_name": "Kaveri-Bank-Online",
            "handle": "Kaveri_Bank_Online",
            "publisher_name": None,
            "developer_id": None,
            "description": "Customer care support for Kaveri Bank users. Direct message for refund and KYC link assistance.",
            "category": None,
            "external_links": ["https://kaveri-support.example"],
            "icon_url": "https://assets.example.org/avatars/separator.png",
            "icon_hash": "0000000000000007",
            "canonical_url": "https://x.example.com/Kaveri_Bank_Online",
            "created_at_source": "2026-09-15T00:00:00Z",
            "followers": 80,
            "following": 2,
            "posts_count": 15,
            "rating_count": None,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaveri-bank-online"],
        },
    }
)

# 3.7 Walkthrough Scenario D: Quiet Attacker with Disclaimer & Copied Avatar (EXACT_NAME_REUSE, score 58 HIGH)
fixtures.append(
    {
        "id": "c-0026",
        "intended_label": "impersonation_exact_name_reuse",
        "asset_type": "SOCIAL_ACCOUNT",
        "platform": "bluesky",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "bluesky",
            "asset_type": "SOCIAL_ACCOUNT",
            "stable_identifier": "did:plc:kaverifansquiet99",
            "secondary_identifiers": {},
            "display_name": "Kaveri Bank Fans",
            "handle": "kaveribankfans.bsky.social",
            "publisher_name": None,
            "developer_id": None,
            "description": "Unofficial fan page, not affiliated.",
            "category": None,
            "external_links": [],
            "icon_url": "https://assets.example.org/avatars/quiet_attacker.png",
            "icon_hash": "0000000000000007",  # 0.95 similarity (copied avatar cancels G5!)
            "canonical_url": "https://bsky.app/profile/kaveribankfans.bsky.social",
            "created_at_source": "2026-10-03T00:00:00Z",  # 9 days old
            "followers": 25,
            "following": 2,
            "posts_count": 4,
            "rating_count": None,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaveri bank fans"],
        },
    }
)

# 3.8 Walkthrough Scenario E: Loud Attacker (ADDED_WORD, score 75 CRITICAL)
fixtures.append(
    {
        "id": "c-0027",
        "intended_label": "impersonation_added_word",
        "asset_type": "SOCIAL_ACCOUNT",
        "platform": "bluesky",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "bluesky",
            "asset_type": "SOCIAL_ACCOUNT",
            "stable_identifier": "did:plc:kavericareattacker77",
            "secondary_identifiers": {},
            "display_name": "Kaveri Bank Care",
            "handle": "kaveribankcare.bsky.social",
            "publisher_name": None,
            "developer_id": None,
            "description": "unofficial, plus customer care, KYC update, verify account immediately.",
            "category": None,
            "external_links": ["https://tinyurl.example/kaveri-kyc"],
            "icon_url": "https://assets.example.org/avatars/loud_attacker.png",
            "icon_hash": "0000000000000007",  # 0.95 similarity
            "canonical_url": "https://bsky.app/profile/kaveribankcare.bsky.social",
            "created_at_source": "2026-09-30T00:00:00Z",  # 12 days old
            "followers": 40,
            "following": 1,
            "posts_count": 3,
            "rating_count": None,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaveri bank care"],
        },
    }
)

# 3.9 Exact Name App with nothing else observable (EXACT_NAME_REUSE, capped at MEDIUM 49)
fixtures.append(
    {
        "id": "c-0028",
        "intended_label": "impersonation_exact_name_reuse",
        "asset_type": "IOS_APP",
        "platform": "apple_app_store",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "apple_app_store",
            "asset_type": "IOS_APP",
            "stable_identifier": "9876543220",
            "secondary_identifiers": {"bundle_id": "com.unknown.kaveribank"},
            "display_name": "Kaveri Bank",
            "handle": None,
            "publisher_name": "Unknown Developer Ltd",
            "developer_id": "9000000099",
            "description": None,
            "category": "Finance",
            "external_links": [],
            "icon_url": None,
            "icon_hash": None,
            "canonical_url": "https://apps.apple.com/app/id9876543220",
            "created_at_source": "2026-09-10T00:00:00Z",
            "followers": None,
            "following": None,
            "posts_count": None,
            "rating_count": 0,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaveri bank"],
        },
    }
)

# 3.10 Repetition: "Kaverrii Bank" (REPETITION)
fixtures.append(
    {
        "id": "c-0029",
        "intended_label": "impersonation_repetition",
        "asset_type": "SOCIAL_ACCOUNT",
        "platform": "instagram",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "instagram",
            "asset_type": "SOCIAL_ACCOUNT",
            "stable_identifier": "handle:kaverrii_bank",
            "secondary_identifiers": {},
            "display_name": "Kaverrii Bank",
            "handle": "kaverrii_bank",
            "publisher_name": None,
            "developer_id": None,
            "description": "Kaverrii Bank regional offers and personal credit loans.",
            "category": None,
            "external_links": ["https://kaverrii.example"],
            "icon_url": "https://assets.example.org/avatars/repetition.png",
            "icon_hash": "0000000000000007",
            "canonical_url": "https://instagram.example.com/kaverrii_bank",
            "created_at_source": "2026-09-18T00:00:00Z",
            "followers": 55,
            "following": 10,
            "posts_count": 12,
            "rating_count": None,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaverrii bank"],
        },
    }
)

# 3.11 Keyboard Adjacent: "Kaveri Bamk" (KEYBOARD_ADJACENT)
fixtures.append(
    {
        "id": "c-0030",
        "intended_label": "impersonation_keyboard_adjacent",
        "asset_type": "SOCIAL_ACCOUNT",
        "platform": "facebook",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "facebook",
            "asset_type": "SOCIAL_ACCOUNT",
            "stable_identifier": "handle:kaveri.bamk",
            "secondary_identifiers": {},
            "display_name": "Kaveri Bamk Official",
            "handle": "kaveri.bamk",
            "publisher_name": None,
            "developer_id": None,
            "description": "Kaveri Bamk official updates, netbanking customer helpline and cashback rewards.",
            "category": None,
            "external_links": ["https://bamk-kaveri.example"],
            "icon_url": "https://assets.example.org/avatars/keyboard.png",
            "icon_hash": "0000000000000007",
            "canonical_url": "https://facebook.example.com/kaveri.bamk",
            "created_at_source": "2026-09-22T00:00:00Z",
            "followers": 60,
            "following": 8,
            "posts_count": 9,
            "rating_count": None,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaveri bamk"],
        },
    }
)

# 3.12 Android Added Word Lure: "Kaveri Bank NetBanking" (ADDED_WORD)
fixtures.append(
    {
        "id": "c-0031",
        "intended_label": "impersonation_added_word",
        "asset_type": "ANDROID_APP",
        "platform": "google_play",
        "source_mode": "SIMULATED",
        "candidate": {
            "source_id": "demo_fixtures",
            "platform": "google_play",
            "asset_type": "ANDROID_APP",
            "stable_identifier": "com.fakekaveri.netbanking",
            "secondary_identifiers": {},
            "display_name": "Kaveri Bank NetBanking",
            "handle": None,
            "publisher_name": "KB NetBanking Team",
            "developer_id": "dev_fake_netbanking",
            "description": "Login to your Kaveri Bank netbanking account. Fast OTP verification and instant fund clearance.",
            "category": "Finance",
            "external_links": ["https://netbanking-kaveribank.example"],
            "icon_url": "https://assets.example.org/icons/android_lure.png",
            "icon_hash": "000000000000000f",
            "canonical_url": "https://play.google.com/store/apps/details?id=com.fakekaveri.netbanking",
            "created_at_source": "2026-10-01T00:00:00Z",
            "followers": None,
            "following": None,
            "posts_count": None,
            "rating_count": 22,
            "source_mode": "SIMULATED",
            "retrieved_at": NOW_ISO,
            "matched_queries": ["kaveri bank netbanking"],
        },
    }
)

# ==============================================================================
# 4. NOT RELEVANT (29 candidates: name similarity < 0.60)
# ==============================================================================
not_relevant_names = [
    "Kalyani Bank",
    "Tungabhadra Bank",
    "Malaprabha Finance",
    "Ghataprabha Credit",
    "Sharavathi Savings",
    "Hemavathi Commerce",
    "Netravathi Mutual",
    "Varada Trust",
    "Aghanashini Pay",
    "Horizon Finance",
    "Metro Credit",
    "Sovereign Pay",
    "Pacific Commerce",
    "Indus Valley Goods",
    "Southern Freight",
    "Ganga Tours",
    "Yamuna Express",
    "Godavari Crafts",
    "Narmada Traders",
    "Tapti Textiles",
    "Krishna Sweets",
    "Mahanadi Steel",
    "Cauvery Handicrafts",
    "Brahmaputra Books",
    "Deccan Heritage Press",
    "Malabar Spices",
    "Konkan Coastal",
    "Nilgiri Tea",
    "Sahyadri Treks",
]

for idx, nr_name in enumerate(not_relevant_names, start=32):
    cid = f"c-{idx:04d}"
    fixtures.append(
        {
            "id": cid,
            "intended_label": "not_relevant",
            "asset_type": "IOS_APP" if idx % 2 == 0 else "SOCIAL_ACCOUNT",
            "platform": "apple_app_store" if idx % 2 == 0 else "bluesky",
            "source_mode": "CACHED" if idx % 3 == 0 else "SIMULATED",
            "candidate": {
                "source_id": "recorded_fixtures" if idx % 3 == 0 else "demo_fixtures",
                "platform": "apple_app_store" if idx % 2 == 0 else "bluesky",
                "asset_type": "IOS_APP" if idx % 2 == 0 else "SOCIAL_ACCOUNT",
                "stable_identifier": f"nr_{idx}_{nr_name.lower().replace(' ', '_')}",
                "secondary_identifiers": {},
                "display_name": nr_name,
                "handle": f"{nr_name.lower().replace(' ', '')}.example",
                "publisher_name": f"{nr_name} Enterprises",
                "developer_id": f"dev_{idx}",
                "description": f"Official services and catalogs for {nr_name}.",
                "category": "Utilities",
                "external_links": [
                    f"https://{nr_name.lower().replace(' ', '')}.example.org"
                ],
                "icon_url": f"https://assets.example.org/icons/nr_{idx}.png",
                "icon_hash": "ffffffffffffffff",  # completely different hash
                "canonical_url": f"https://apps.example.org/{idx}",
                "created_at_source": "2020-01-01T00:00:00Z",
                "followers": 500 if idx % 2 != 0 else None,
                "following": 100 if idx % 2 != 0 else None,
                "posts_count": 250 if idx % 2 != 0 else None,
                "rating_count": 1500 if idx % 2 == 0 else None,
                "source_mode": "CACHED" if idx % 3 == 0 else "SIMULATED",
                "retrieved_at": PAST_ISO if idx % 3 == 0 else NOW_ISO,
                "matched_queries": ["bank"],
            },
        }
    )

manifest_path = Path(__file__).parent / "fixtures_manifest.json"
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump({"total": len(fixtures), "fixtures": fixtures}, f, indent=2)

print(f"Generated {len(fixtures)} fixtures in {manifest_path}")
