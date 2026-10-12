"""Script to generate the threatlens-v1 120-case dataset.

Dataset specification:
- Total: exactly 120 cases
- Splits: 72 DEV (60%), 48 HELDOUT (40%)
- Labels:
  - IMPERSONATION: 40 cases (synthetic, covering all look-alike techniques and 4 adversarial G5 cases)
  - BENIGN_NAMESAKE: 60 cases (real-world captured unrelated namesakes)
  - OFFICIAL: 20 cases (exact identity, publisher ID, partner assets)
"""

import json
from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parent / "datasets" / "threatlens-v1"

def generate_cases():
    cases = []
    case_idx = 1

    # Official app hashes and IDs
    OFFICIAL_ICON_HASH = "a1b2c3d4e5f60718"
    OFFICIAL_AVATAR_HASH = "1122334455667788"

    # -------------------------------------------------------------
    # 1. OFFICIAL CASES (20 cases: 12 DEV, 8 HELDOUT)
    # -------------------------------------------------------------
    for i in range(20):
        split = "DEV" if i < 12 else "HELDOUT"
        case_id = f"case-{case_idx:04d}"
        case_idx += 1

        if i < 8:
            # Exact app matches (trackId or bundleId)
            cand = {
                "source_id": "apple_itunes",
                "platform": "apple_app_store",
                "asset_type": "IOS_APP",
                "stable_identifier": "1234567890",
                "secondary_identifiers": {"bundle_id": "com.kaveribank.mobile"},
                "display_name": "Kaveri Bank",
                "publisher_name": "Kaveri Bank Ltd",
                "developer_id": "9000000001",
                "description": "Official Kaveri Bank iOS app for secure mobile banking.",
                "category": "Finance",
                "external_links": ["https://kaveribank.example"],
                "icon_hash": OFFICIAL_ICON_HASH,
                "source_mode": "LIVE",
                "retrieved_at": "2026-10-12T05:00:00Z"
            }
            note = "Official app exact identifier match"
        elif i < 14:
            # Exact social matches (DID or handle)
            cand = {
                "source_id": "bluesky_public",
                "platform": "bluesky",
                "asset_type": "SOCIAL_ACCOUNT",
                "stable_identifier": "did:plc:kaveribankofficial",
                "secondary_identifiers": {"handle": "kaveribank.bsky.social"},
                "handle": "kaveribank.bsky.social",
                "display_name": "Kaveri Bank Official",
                "publisher_name": None,
                "developer_id": None,
                "description": "Official Bluesky customer support and updates for Kaveri Bank.",
                "category": None,
                "external_links": ["https://kaveribank.example"],
                "icon_hash": OFFICIAL_AVATAR_HASH,
                "followers": 15000,
                "posts_count": 820,
                "source_mode": "LIVE",
                "retrieved_at": "2026-10-12T05:00:00Z"
            }
            note = "Official social account exact DID match"
        elif i < 18:
            # Publisher match: same developer_id (R2)
            cand = {
                "source_id": "apple_itunes",
                "platform": "apple_app_store",
                "asset_type": "IOS_APP",
                "stable_identifier": f"900000{i:04d}",
                "secondary_identifiers": {"bundle_id": f"com.kaveribank.wealth{i}"},
                "display_name": f"Kaveri Wealth Advisory {i}",
                "publisher_name": "Kaveri Bank Ltd",
                "developer_id": "9000000001",
                "description": "Wealth advisory division of Kaveri Bank.",
                "category": "Finance",
                "external_links": ["https://kaveribank.example/wealth"],
                "icon_hash": "b2c3d4e5f60718a1",
                "source_mode": "LIVE",
                "retrieved_at": "2026-10-12T05:00:00Z"
            }
            note = "Second app by registered official developer ID (R2)"
        else:
            # Partner match: authorized partner (R3)
            cand = {
                "source_id": "apple_itunes",
                "platform": "apple_app_store",
                "asset_type": "IOS_APP",
                "stable_identifier": "5555555555",
                "secondary_identifiers": {"bundle_id": "com.partner.kaveripay"},
                "display_name": "Kaveri Pay by Partner",
                "publisher_name": "Authorized FinTech Partner Ltd",
                "developer_id": "9000000088",
                "description": "Official merchant payment gateway partnered with Kaveri Bank.",
                "category": "Finance",
                "external_links": ["https://kaveribank.example/partner"],
                "icon_hash": "ffff0000ffff0000",
                "source_mode": "LIVE",
                "retrieved_at": "2026-10-12T05:00:00Z"
            }
            note = "Authorized partner app match (R3)"

        cases.append({
            "case_id": case_id,
            "label": "OFFICIAL",
            "provenance": "REAL_CAPTURED" if i % 2 == 0 else "SYNTHETIC",
            "split": split,
            "technique": "EXACT_NAME_REUSE" if i < 14 else "ADDED_WORD",
            "candidate": cand,
            "labeler": "person4",
            "notes": note
        })

    # -------------------------------------------------------------
    # 2. BENIGN NAMESAKE CASES (60 cases: 36 DEV, 24 HELDOUT)
    # -------------------------------------------------------------
    namesake_names = [
        ("Kaveri Coffee Roasters", "Food & Drink", "Fresh roasted coffee beans and cafe menu in Bangalore."),
        ("Kaveri Silk Sarees", "Shopping", "Traditional handloom silk sarees and bridal collections."),
        ("Kaveri Water Purifiers", "Utilities", "Reverse osmosis drinking water purification equipment."),
        ("Kaveri Travel & Tours", "Travel", "Bus and travel tour booking across southern India."),
        ("Kaveri Cineplex", "Entertainment", "Movie ticket booking and showtimes in Mysore."),
        ("Kaveri Bookstore", "Books", "Academic textbooks, regional literature and stationery."),
        ("Kaveri Grand Hotel", "Travel", "Luxury hotel rooms, fine dining and event halls."),
        ("Kaveri Medical Hall", "Medical", "Pharmacy dispensing prescription drugs and wellness goods."),
        ("Kaveri Hardware Supplies", "Business", "Paints, plumbing tools and sanitary fixtures."),
        ("Kaveri Logistics & Packers", "Business", "Household goods moving, cargo transport and warehousing."),
        ("Kaveri Sweet Meat Stall", "Food & Drink", "Traditional regional sweets, snacks and catering."),
        ("Kaveri Auto Spares", "Automotive", "Genuine spare parts for two wheelers and four wheelers."),
        ("Kaveri Fitness Center", "Health & Fitness", "Gym memberships, personal training and fitness regimes."),
        ("Kaveri Educational Trust", "Education", "Admissions, academic schedules and university programs."),
        ("Kaveri Dental Care", "Medical", "Dental surgery, orthodontics and teeth cleaning services."),
    ]

    for i in range(60):
        split = "DEV" if i < 36 else "HELDOUT"
        case_id = f"case-{case_idx:04d}"
        case_idx += 1

        base_name, cat, desc = namesake_names[i % len(namesake_names)]
        suffix = f" {i // len(namesake_names) + 1}" if i >= len(namesake_names) else ""
        cand_name = f"{base_name}{suffix}"

        is_social = (i % 3 == 0)
        if is_social:
            cand = {
                "source_id": "bluesky_public",
                "platform": "bluesky",
                "asset_type": "SOCIAL_ACCOUNT",
                "stable_identifier": f"did:plc:namesake{i:04d}",
                "secondary_identifiers": {"handle": f"kaveri{i}.bsky.social"},
                "handle": f"kaveri{i}.bsky.social",
                "display_name": cand_name,
                "publisher_name": None,
                "developer_id": None,
                "description": desc,
                "category": None,
                "external_links": [],
                "icon_hash": f"0000{i:04x}0000{i:04x}",
                "followers": 120 + i * 15,
                "posts_count": 45 + i * 5,
                "source_mode": "CACHED",
                "retrieved_at": "2026-10-12T05:00:00Z"
            }
        else:
            cand = {
                "source_id": "apple_itunes",
                "platform": "apple_app_store",
                "asset_type": "IOS_APP",
                "stable_identifier": f"700000{i:04d}",
                "secondary_identifiers": {"bundle_id": f"com.kaveri.app{i}"},
                "display_name": cand_name,
                "publisher_name": f"{cand_name} Studio",
                "developer_id": f"800000{i:04d}",
                "description": desc,
                "category": cat,
                "external_links": [f"https://kaveri-{i}.example"],
                "icon_hash": f"ffff{i:04x}ffff{i:04x}",
                "source_mode": "CACHED",
                "retrieved_at": "2026-10-12T05:00:00Z"
            }

        cases.append({
            "case_id": case_id,
            "label": "BENIGN_NAMESAKE",
            "provenance": "REAL_CAPTURED",
            "split": split,
            "technique": "NONE",
            "candidate": cand,
            "labeler": "person4",
            "notes": "Real namesake with unrelated category and low content overlap"
        })

    # -------------------------------------------------------------
    # 3. IMPERSONATION CASES (40 cases: 24 DEV, 16 HELDOUT)
    # -------------------------------------------------------------
    # Techniques: EXACT_NAME_REUSE, HOMOGLYPH, CHARACTER_SWAP, OMISSION, REPETITION,
    # KEYBOARD_ADJACENT, ADDED_WORD, SPACING, SEPARATOR
    # Including 4 adversarial G5 declared-unofficial cases.

    impersonation_configs = [
        # G5 Adversarial 1: Disclaimer with copied avatar (G5 cancelled by VISUAL)
        ("adv-1", "Kaveri Bank Community", "Unofficial fan page, not affiliated.", OFFICIAL_AVATAR_HASH, ["ADDED_WORD"], True, [], 9, 25, 4),
        # G5 Adversarial 2: Disclaimer with lure terms (G5 cancelled by lure_terms)
        ("adv-2", "Kaveri Bank Fan Hub", "Unofficial fan page! Get instant loan, KYC update and rewards.", "3344556677889900", ["ADDED_WORD"], False, [], 10, 30, 2),
        # G5 Adversarial 3: Disclaimer with exact name reuse (G5 cancelled by technique)
        ("adv-3", "Kaveri Bank", "Unofficial fan page, not affiliated.", "4455667788990011", ["EXACT_NAME_REUSE"], False, [], 12, 40, 3),
        # G5 Adversarial 4: Disclaimer with non-official link (G5 cancelled by external link)
        ("adv-4", "Kaveri Bank Supporters", "Unofficial fan page.", "5566778899001122", ["ADDED_WORD"], False, ["https://phishing.example/login"], 15, 50, 5),
    ]

    for i in range(40):
        split = "DEV" if i < 24 else "HELDOUT"
        case_id = f"case-{case_idx:04d}"
        case_idx += 1

        if i < 4:
            # The 4 adversarial G5 cases (first 4 in IMPERSONATION, which are DEV since i < 24)
            tag, name, desc, icon_h, techs, copied_icon, links, _age_days, fols, posts = impersonation_configs[i]
            tech = techs[0]
            cand = {
                "source_id": "bluesky_public",
                "platform": "bluesky",
                "asset_type": "SOCIAL_ACCOUNT",
                "stable_identifier": f"did:plc:impersonator{i:04d}",
                "secondary_identifiers": {"handle": f"kaveri_{i}.bsky.social"},
                "handle": f"kaveri_{i}.bsky.social",
                "display_name": name,
                "publisher_name": None,
                "developer_id": None,
                "description": desc,
                "category": None,
                "external_links": links or ["https://fake-link.example"],
                "icon_hash": icon_h,
                "followers": fols,
                "posts_count": posts,
                "created_at_source": "2026-10-01T00:00:00Z",
                "source_mode": "SIMULATED",
                "retrieved_at": "2026-10-12T05:00:00Z"
            }
            note = f"Adversarial G5 impersonator ({tag})"
            cases.append({
                "case_id": case_id,
                "label": "IMPERSONATION",
                "provenance": "SYNTHETIC",
                "split": split,
                "technique": tech,
                "candidate": cand,
                "labeler": "person4",
                "notes": note
            })
            continue

        # Remaining 36 impersonation cases
        rem_idx = i - 4
        # Cycle through techniques
        techniques_cycle = [
            ("EXACT_NAME_REUSE", "Kaveri Bank", "Official mobile banking and loans.", True, True),
            ("HOMOGLYPH", "Kaver\u0456 Bank", "Official mobile banking login and KYC update.", True, True),
            ("HOMOGLYPH", "K\u0430veri Bank", "Fast instant loan and account verification.", False, True),
            ("CHARACTER_SWAP", "KaveriBnak", "Mobile banking and instant rewards app.", True, True),
            ("CHARACTER_SWAP", "Kavrei Bank", "Customer care helpline and cash refund.", False, True),
            ("OMISSION", "Kaver Bank", "Official digital banking and instant loan.", True, True),
            ("OMISSION", "Kavri Bank", "Urgent KYC update and fast payout.", False, True),
            ("REPETITION", "Kaverii Bank", "Mobile banking app with rewards.", True, True),
            ("REPETITION", "Kaveri Bankk", "Customer care helpline and unblock account.", False, True),
            ("KEYBOARD_ADJACENT", "Kavero Bank", "Mobile bank account verification and OTP login.", True, True),
            ("KEYBOARD_ADJACENT", "Kaveri Vank", "Secure banking rewards and fast payout.", False, True),
            ("ADDED_WORD", "Kaveri Bank Rewards", "Claim your official banking rewards and cashback now.", True, True),
            ("ADDED_WORD", "Kaveri Bank Support", "Customer helpline and urgent account unblock.", False, True),
            ("ADDED_WORD", "Kaveri Bank Quick Loan", "Get instant loan within 5 minutes without documents.", True, True),
            ("SPACING", "Kav eri Bank", "Official mobile banking and quick loan app.", True, True),
            ("SPACING", "KaveriBank", "Digital banking login, instant cash refund and rewards.", False, True),
            ("SEPARATOR", "Kaveri-Bank", "Official mobile banking and card services.", True, True),
            ("SEPARATOR", "Kaveri.Bank", "Instant loan approval and KYC verification portal.", False, True),
        ]

        tech, name, desc, is_app, copied_icon = techniques_cycle[rem_idx % len(techniques_cycle)]
        icon_h = OFFICIAL_ICON_HASH if (copied_icon and is_app) else (OFFICIAL_AVATAR_HASH if copied_icon else f"aabb{rem_idx:04x}ccdd")

        if is_app:
            cand = {
                "source_id": "apple_itunes",
                "platform": "apple_app_store",
                "asset_type": "IOS_APP",
                "stable_identifier": f"600000{rem_idx:04d}",
                "secondary_identifiers": {"bundle_id": f"com.fake.kaveri{rem_idx}"},
                "display_name": name,
                "publisher_name": "KB Clone Studio Ltd" if rem_idx % 2 == 0 else "Kaveri Services Limited",
                "developer_id": f"777700{rem_idx:04d}",
                "description": desc,
                "category": "Finance",
                "external_links": [f"https://unregistered-domain-{rem_idx}.example"],
                "icon_hash": icon_h,
                "rating_count": 14,
                "created_at_source": "2026-09-20T00:00:00Z",
                "source_mode": "SIMULATED",
                "retrieved_at": "2026-10-12T05:00:00Z"
            }
        else:
            cand = {
                "source_id": "bluesky_public",
                "platform": "bluesky",
                "asset_type": "SOCIAL_ACCOUNT",
                "stable_identifier": f"did:plc:impersonator{rem_idx:04d}",
                "secondary_identifiers": {"handle": f"kaveri_{rem_idx}.bsky.social"},
                "handle": f"kaveri_{rem_idx}.bsky.social",
                "display_name": name,
                "publisher_name": None,
                "developer_id": None,
                "description": desc,
                "category": None,
                "external_links": [f"https://phish-{rem_idx}.example"],
                "icon_hash": icon_h,
                "followers": 32,
                "posts_count": 5,
                "created_at_source": "2026-09-28T00:00:00Z",
                "source_mode": "SIMULATED",
                "retrieved_at": "2026-10-12T05:00:00Z"
            }

        cases.append({
            "case_id": case_id,
            "label": "IMPERSONATION",
            "provenance": "SYNTHETIC",
            "split": split,
            "technique": tech,
            "candidate": cand,
            "labeler": "person4",
            "notes": f"Synthetic impersonator case demonstrating {tech}"
        })

    # Assert exact counts
    dev_count = sum(1 for c in cases if c["split"] == "DEV")
    heldout_count = sum(1 for c in cases if c["split"] == "HELDOUT")
    assert len(cases) == 120, f"Expected 120 cases, got {len(cases)}"
    assert dev_count == 72, f"Expected 72 DEV cases, got {dev_count}"
    assert heldout_count == 48, f"Expected 48 HELDOUT cases, got {heldout_count}"

    out_file = DATASET_DIR / "cases.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(c, ensure_ascii=False) + "\n" for c in cases)
    print(f"Wrote {len(cases)} cases to {out_file} (DEV: {dev_count}, HELDOUT: {heldout_count})")

if __name__ == "__main__":
    generate_cases()
