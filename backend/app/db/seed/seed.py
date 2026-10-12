"""Idempotent seed script for ThreatLens Kaveri Bank demo story (Appendix B)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.db.base import generate_uuid
from app.db.models import (
    Assessment,
    Brand,
    Evidence,
    OfficialAsset,
    Scan,
)
from app.db.session import create_db_engine, init_db
from app.repositories.sqlalchemy_repo import (
    SqlAlchemyAssessmentRepo,
    SqlAlchemyCandidateRepo,
)
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

MANIFEST_PATH = Path(__file__).parent / "fixtures_manifest.json"
DEMO_SCAN_ID = "00000000-0000-4000-8000-000000000001"
DEMO_BRAND_NAME = "Kaveri Bank"


def load_fixtures_manifest() -> list[dict[str, Any]]:
    """Load machine-readable demo fixtures manifest."""
    if not MANIFEST_PATH.exists():
        from .generate_manifest import fixtures  # fallback if file not written

        return fixtures
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        data = json.load(f)
        return data.get("fixtures", [])


def seed_demo_story(
    session_factory: sessionmaker[Session] | None = None,
    engine=None,
) -> dict[str, Any]:
    """Load the full Kaveri Bank demo story into the database idempotently."""
    if session_factory is None:
        if engine is None:
            engine = create_db_engine()
        init_db(engine)
        session_factory = sessionmaker(
            bind=engine, class_=Session, expire_on_commit=False
        )

    candidate_repo = SqlAlchemyCandidateRepo(session_factory)
    assessment_repo = SqlAlchemyAssessmentRepo(session_factory)

    fixtures = load_fixtures_manifest()

    with session_factory() as session:
        # 1. Brand (Kaveri Bank)
        brand = session.execute(
            select(Brand).where(Brand.name == DEMO_BRAND_NAME)
        ).scalar_one_or_none()

        if brand is None:
            brand_id = generate_uuid()
            brand = Brand(
                id=brand_id,
                name=DEMO_BRAND_NAME,
                description="Fictional regional commercial bank in South India used for ThreatLens demo and QA fixtures.",
                official_domains=["kaveribank.example"],
                keywords=[
                    "kaveri",
                    "kaveri bank",
                    "kaveri mobile",
                    "kaveri netbanking",
                ],
                distinctive_tokens=["kaveri"],
                generic_tokens_extra=["bank", "mobile", "rewards", "wealth"],
                industry_category="Banking / Financial Services",
                demo_brand=True,
            )
            session.add(brand)
            session.commit()
            session.refresh(brand)

        brand_id = brand.id

        # 2. Official Assets (4 core registered assets)
        official_definitions = [
            {
                "platform": "apple_app_store",
                "asset_type": "IOS_APP",
                "stable_identifier": "1234567890",
                "secondary_identifiers": {"bundle_id": "com.kaveribank.mobile"},
                "display_name": "Kaveri Bank",
                "developer_id": "9000000001",
                "publisher_name": "Kaveri Bank Ltd",
                "canonical_url": "https://apps.apple.com/in/app/kaveri-bank/id1234567890",
                "icon_url": "https://assets.example.org/icons/kb_official.png",
                "icon_hash": "0000000000000000",
                "relationship": "OFFICIAL",
                "verification_method": "DOMAIN_DNS",
                "is_verified": True,
                "trust_publisher": True,
                "is_active": True,
            },
            {
                "platform": "bluesky",
                "asset_type": "SOCIAL_ACCOUNT",
                "stable_identifier": "did:plc:kaveriofficial123",
                "secondary_identifiers": {},
                "display_name": "Kaveri Bank",
                "handle": "kaveribank.example",
                "canonical_url": "https://bsky.app/profile/kaveribank.example",
                "icon_url": "https://assets.example.org/avatars/kb_bsky.png",
                "icon_hash": "0000000000000000",
                "relationship": "OFFICIAL",
                "verification_method": "DOMAIN_DID",
                "is_verified": True,
                "trust_publisher": True,
                "is_active": True,
            },
            {
                "platform": "apple_app_store",
                "asset_type": "IOS_APP",
                "stable_identifier": "1234567899",
                "secondary_identifiers": {"bundle_id": "com.kaveribank.partner"},
                "display_name": "Kaveri Merchant Connect",
                "developer_id": "9000000099",
                "publisher_name": "Kaveri Partner Solutions",
                "canonical_url": "https://apps.apple.com/in/app/kaveri-merchant/id1234567899",
                "icon_url": "https://assets.example.org/icons/kb_partner.png",
                "icon_hash": "0000000000000000",
                "relationship": "AUTHORIZED_PARTNER",
                "verification_method": "LEGAL_CONTRACT",
                "is_verified": True,
                "trust_publisher": True,
                "is_active": True,
            },
            {
                "platform": "google_play",
                "asset_type": "ANDROID_APP",
                "stable_identifier": "com.kaveribank.android",
                "secondary_identifiers": {"package_name": "com.kaveribank.android"},
                "display_name": "Kaveri Bank Mobile",
                "developer_id": "Kaveri Bank Ltd",
                "publisher_name": "Kaveri Bank Ltd",
                "canonical_url": "https://play.google.com/store/apps/details?id=com.kaveribank.android",
                "icon_url": "https://assets.example.org/icons/kb_android.png",
                "icon_hash": "0000000000000000",
                "relationship": "OFFICIAL",
                "verification_method": "PLAY_SIGNING",
                "is_verified": True,
                "trust_publisher": True,
                "is_active": True,
            },
        ]

        official_assets_map: dict[str, str] = {}
        for o_def in official_definitions:
            existing_asset = session.execute(
                select(OfficialAsset).where(
                    OfficialAsset.brand_id == brand_id,
                    OfficialAsset.platform == o_def["platform"],
                    OfficialAsset.stable_identifier == o_def["stable_identifier"],
                )
            ).scalar_one_or_none()

            if existing_asset is None:
                new_asset = OfficialAsset(
                    id=generate_uuid(),
                    brand_id=brand_id,
                    **o_def,
                )
                session.add(new_asset)
                session.commit()
                session.refresh(new_asset)
                official_assets_map[o_def["stable_identifier"]] = new_asset.id
            else:
                for k, v in o_def.items():
                    setattr(existing_asset, k, v)
                session.commit()
                session.refresh(existing_asset)
                official_assets_map[o_def["stable_identifier"]] = existing_asset.id

        # 3. Demo Scan
        scan = session.execute(
            select(Scan).where(Scan.id == DEMO_SCAN_ID)
        ).scalar_one_or_none()

        scan_data = {
            "mode": "STANDARD",
            "status": "COMPLETED",
            "stage": "COMPLETE",
            "progress_percent": 100,
            "options": {"demo": True, "fixture_version": "appendix_b"},
            "source_outcomes": [
                {"source_id": "apple_itunes", "status": "OK", "candidates_count": 25},
                {"source_id": "google_play", "status": "OK", "candidates_count": 15},
                {"source_id": "bluesky_public", "status": "OK", "candidates_count": 20},
            ],
            "funnel": {
                "deduplicated": 60,
                "official_cleared": 5,
                "not_relevant": 29,
                "benign_lookalike": 14,
                "below_threshold": 0,
                "findings": 12,
            },
            "findings_by_severity": {
                "CRITICAL": 3,
                "HIGH": 8,
                "MEDIUM": 1,
                "LOW": 0,
            },
            "events": [
                {
                    "stage": "INITIALIZE",
                    "message": "Demo scan initialized for Kaveri Bank",
                    "timestamp": "2026-10-12T05:30:00Z",
                },
                {
                    "stage": "DISCOVERY",
                    "message": "Discovered 60 candidates across 3 sources",
                    "timestamp": "2026-10-12T05:30:10Z",
                },
                {
                    "stage": "SCORING",
                    "message": "Assessed 60 candidates against Appendix B rules",
                    "timestamp": "2026-10-12T05:30:20Z",
                },
                {
                    "stage": "COMPLETE",
                    "message": "Demo scan complete with 12 findings and 5 cleared",
                    "timestamp": "2026-10-12T05:30:25Z",
                },
            ],
        }

        if scan is None:
            scan = Scan(id=DEMO_SCAN_ID, brand_id=brand_id, **scan_data)
            session.add(scan)
            session.commit()
            session.refresh(scan)
        else:
            for k, v in scan_data.items():
                setattr(scan, k, v)
            session.commit()
            session.refresh(scan)

        # Clear existing assessments and evidence for this demo scan to guarantee idempotence
        session.execute(delete(Evidence).where(Evidence.scan_id == DEMO_SCAN_ID))
        session.execute(delete(Assessment).where(Assessment.scan_id == DEMO_SCAN_ID))
        session.commit()

    # 4. Upsert Candidates and Save Assessments
    for f_item in fixtures:
        f_id = f_item["id"]
        intended_label = f_item["intended_label"]
        cand_dict = f_item["candidate"]

        # Upsert into candidate_assets table
        saved_cand = candidate_repo.upsert(
            candidate=cand_dict,
            brand_id=brand_id,
            scan_id=DEMO_SCAN_ID,
        )
        cand_id = saved_cand["id"]

        # Compute assessment outcome from intended fixture label
        matched_id: str | None = None
        evidence_list: list[dict[str, Any]] = []

        if intended_label == "cleared_r1":
            identity_decision = "CLEARED_BY_IDENTITY"
            risk_score = 0
            severity = None
            technique = "NONE"
            if cand_dict.get("platform") == "apple_app_store":
                matched_id = official_assets_map.get("1234567890")
                rule = "R1_EXACT_ID"
                explanation = "Exact bundle ID match com.kaveribank.mobile against registered official iOS asset."
            elif cand_dict.get("platform") == "bluesky":
                matched_id = official_assets_map.get("did:plc:kaveriofficial123")
                rule = "R1_EXACT_ID"
                explanation = "Exact DID match did:plc:kaveriofficial123 against registered official Bluesky asset."
            else:
                matched_id = official_assets_map.get("com.kaveribank.android")
                rule = "R1_EXACT_ID"
                explanation = "Exact package name match com.kaveribank.android against registered official Android asset."

            evidence_list.append(
                {
                    "source_id": cand_dict.get("source_id", "demo"),
                    "evidence_type": "EXACT_IDENTIFIER_MATCH",
                    "status": "OBSERVED",
                    "field_name": "stable_identifier",
                    "observed_value": cand_dict.get("stable_identifier"),
                    "source_url": cand_dict.get("canonical_url"),
                    "notes": f"Identity matched under rule {rule}",
                }
            )

        elif intended_label == "cleared_r2":
            identity_decision = "CLEARED_BY_IDENTITY"
            matched_id = official_assets_map.get("1234567890")
            rule = "R2_PUBLISHER_ID"
            risk_score = 0
            severity = None
            technique = "NONE"
            explanation = (
                "Developer ID 9000000001 matches registered official developer ID."
            )
            evidence_list.append(
                {
                    "source_id": cand_dict.get("source_id", "demo"),
                    "evidence_type": "DEVELOPER_ID_MATCH",
                    "status": "OBSERVED",
                    "field_name": "developer_id",
                    "observed_value": "9000000001",
                    "source_url": cand_dict.get("canonical_url"),
                    "notes": "Publisher ID matched under rule R2",
                }
            )

        elif intended_label == "cleared_r3":
            identity_decision = "CLEARED_BY_IDENTITY"
            matched_id = official_assets_map.get("1234567899")
            rule = "R3_PARTNER"
            risk_score = 0
            severity = None
            technique = "NONE"
            explanation = "Matches authorized partner asset com.kaveribank.partner."
            evidence_list.append(
                {
                    "source_id": cand_dict.get("source_id", "demo"),
                    "evidence_type": "PARTNER_BUNDLE_MATCH",
                    "status": "OBSERVED",
                    "field_name": "secondary_identifiers.bundle_id",
                    "observed_value": "com.kaveribank.partner",
                    "source_url": cand_dict.get("canonical_url"),
                    "notes": "Authorized partner asset cleared under rule R3",
                }
            )

        elif intended_label == "benign_g5":
            identity_decision = "BENIGN_LOOKALIKE"
            rule = "G5_DECLARED_UNOFFICIAL"
            severity = "LOW"
            technique = "FAN_PAGE"
            if f_id == "c-0006":
                explanation = "Honest declared fan page with non-copied avatar and disclaimer (matching Scenario B)."
                risk_score = 15
            else:
                explanation = "Declared fan page quoting brand text with non-copied avatar (matching Scenario C)."
                risk_score = 18
            evidence_list.append(
                {
                    "source_id": cand_dict.get("source_id", "demo"),
                    "evidence_type": "FAN_PAGE_DISCLAIMER",
                    "status": "OBSERVED",
                    "field_name": "description",
                    "observed_value": cand_dict.get("description"),
                    "source_url": cand_dict.get("canonical_url"),
                    "notes": "Unofficial fan page disclaimer observed with benign icon hash",
                }
            )

        elif intended_label == "benign_g4":
            identity_decision = "BENIGN_LOOKALIKE"
            severity = "LOW"
            technique = "LOOKALIKE"
            cat = cand_dict.get("category")
            if cat:
                rule = "G4_UNRELATED_CATEGORY"
                explanation = f"App Store category '{cat}' is completely unrelated to financial services."
                risk_score = 10
            else:
                rule = "G4_LOW_CONTENT_OVERLAP"
                explanation = "Social community profile with no financial services or banking content overlap."
                risk_score = 8
            evidence_list.append(
                {
                    "source_id": cand_dict.get("source_id", "demo"),
                    "evidence_type": "UNRELATED_CATEGORY_OVERLAP",
                    "status": "OBSERVED",
                    "field_name": "category",
                    "observed_value": cat or "Social",
                    "source_url": cand_dict.get("canonical_url"),
                    "notes": "Categorical mismatch with financial institutions",
                }
            )

        elif intended_label.startswith("impersonation_"):
            identity_decision = "CANDIDATE_FOR_REVIEW"
            rule = "SUSPICIOUS_IMPERSONATION"
            tech_map = {
                "impersonation_added_word": "ADDED_WORD",
                "impersonation_homoglyph": "HOMOGLYPH",
                "impersonation_character_swap": "CHARACTER_SWAP",
                "impersonation_omission": "OMISSION",
                "impersonation_spacing": "SPACING",
                "impersonation_separator": "SEPARATOR",
                "impersonation_exact_name_reuse": "EXACT_NAME_REUSE",
                "impersonation_repetition": "REPETITION",
                "impersonation_keyboard_adjacent": "KEYBOARD_ADJACENT",
            }
            technique = tech_map.get(intended_label, "LOOKALIKE")

            if f_id == "c-0020":
                risk_score = 72
                severity = "HIGH"
                explanation = "Scenario A: Fake app 'Kaveri Bank Rewards' with copied icon (similarity 0.93), non-official seller link, and lure terms."
            elif f_id == "c-0021":
                risk_score = 85
                severity = "CRITICAL"
                explanation = "Homoglyph Cyrillic U+0456 substitution with copied icon and banking phishing portal."
            elif f_id == "c-0022":
                risk_score = 78
                severity = "HIGH"
                explanation = "Character swap typo 'KaveriBnak' targeting mobile app store with KYC verification lure."
            elif f_id == "c-0023":
                risk_score = 76
                severity = "HIGH"
                explanation = "Character omission typo 'Kaver Bank' with copied icon."
            elif f_id == "c-0024":
                risk_score = 68
                severity = "HIGH"
                explanation = "Double space evasion 'Kaveri  Bank' on Bluesky soliciting instant loan approval."
            elif f_id == "c-0025":
                risk_score = 70
                severity = "HIGH"
                explanation = "Hyphenated brand impersonator 'Kaveri-Bank-Online' soliciting direct messages for refunds."
            elif f_id == "c-0026":
                risk_score = 58
                severity = "HIGH"
                explanation = "Scenario D: Quiet attacker with disclaimer but copied avatar (similarity 0.95), defeating G5 exemption."
            elif f_id == "c-0027":
                risk_score = 88
                severity = "CRITICAL"
                explanation = "Scenario E: Loud attacker with disclaimer, copied avatar, and aggressive KYC phishing."
            elif f_id == "c-0028":
                risk_score = 49
                severity = "MEDIUM"
                explanation = (
                    "Exact-name app with nothing else observable, capped at MEDIUM."
                )
            elif f_id == "c-0029":
                risk_score = 65
                severity = "HIGH"
                explanation = "Character repetition 'Kaverrii Bank' on Instagram targeting regional credit loans."
            elif f_id == "c-0030":
                risk_score = 64
                severity = "HIGH"
                explanation = "Keyboard-adjacent typo 'Kaveri Bamk' on Facebook targeting netbanking users."
            elif f_id == "c-0031":
                risk_score = 82
                severity = "CRITICAL"
                explanation = "Android netbanking phishing lure 'Kaveri Bank NetBanking' targeting login credentials."
            else:
                risk_score = 60
                severity = "HIGH"
                explanation = (
                    "Suspicious brand impersonation targeting customer credentials."
                )

            evidence_list.append(
                {
                    "source_id": cand_dict.get("source_id", "demo"),
                    "evidence_type": "IMPERSONATION_SIGNAL",
                    "status": "OBSERVED",
                    "field_name": "display_name",
                    "observed_value": cand_dict.get("display_name"),
                    "source_url": cand_dict.get("canonical_url"),
                    "notes": f"Detected technique {technique} with risk score {risk_score}",
                }
            )

        else:  # not_relevant
            identity_decision = "BELOW_THRESHOLD"
            rule = "NOT_RELEVANT"
            risk_score = 5
            severity = None
            technique = "NONE"
            explanation = "Name similarity score clearly below 0.60 threshold."
            evidence_list.append(
                {
                    "source_id": cand_dict.get("source_id", "demo"),
                    "evidence_type": "STRING_SIMILARITY",
                    "status": "OBSERVED",
                    "field_name": "display_name",
                    "observed_value": cand_dict.get("display_name"),
                    "source_url": cand_dict.get("canonical_url"),
                    "notes": "Low lexical similarity to brand token",
                }
            )

        result_payload = {
            "identity_decision": identity_decision,
            "rule": rule,
            "matched_official_asset_id": matched_id,
            "risk_score": risk_score,
            "severity": severity,
            "evidence_coverage": 0.85
            if identity_decision == "CANDIDATE_FOR_REVIEW"
            else None,
            "corroborating_groups": ["NAME", "VISUAL"]
            if risk_score and risk_score >= 70
            else ["NAME"],
            "gates_applied": ["G5_OVERRIDDEN_BY_COPY"]
            if f_id in {"c-0026", "c-0027"}
            else [],
            "score_breakdown": [{"group": "NAME", "points": 35.0}],
            "technique": technique,
            "explanation": explanation,
            "source_mode": cand_dict.get("source_mode", "SIMULATED"),
            "scoring_version": "3.0.0",
        }

        assessment_repo.save(
            scan_id=DEMO_SCAN_ID,
            candidate_id=cand_id,
            result=result_payload,
            evidence=evidence_list,
            brand_id=brand_id,
        )

    return {
        "brand_id": brand_id,
        "scan_id": DEMO_SCAN_ID,
        "total_seeded": len(fixtures),
        "cleared_count": 5,
        "lookalike_count": 14,
        "findings_count": 12,
        "not_relevant_count": 29,
    }


if __name__ == "__main__":
    summary = seed_demo_story()
    print("Successfully loaded ThreatLens Kaveri Bank demo story:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
