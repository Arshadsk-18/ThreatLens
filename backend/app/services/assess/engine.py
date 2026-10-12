"""Master assessment engine for ThreatLens v3.

Pure function, no network, no database.
Signature:
def assess(candidate: NormalizedCandidate, brand: BrandCtx, official_assets: list[OfficialAssetCtx], config: ScoringConfig) -> AssessmentResult

Follows the pipeline from Sections 5.2, 7, 8.2, 8.3, 8.4, 8.4a, 8.5, and 12.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from backend.app.services.identity_guard.guard import evaluate_identity_guard
from backend.app.services.normalization.name_similarity import (
    calculate_name_similarity,
    calculate_social_name_similarity,
)
from backend.app.services.normalization.techniques import (
    LookalikeTechnique,
    classify_technique,
)
from backend.app.services.query_planner.models import (
    AssetType,
    BrandCtx,
    IdentityDecision,
    OfficialAssetCtx,
    Relationship,
)
from backend.app.services.scoring.evaluators import (
    DISCLAIMER_TERMS,
    count_lexicon_hits,
    evaluate_app_signals,
    evaluate_social_signals,
    extract_domain,
)
from backend.app.services.scoring.models import (
    AssessmentResult,
    EvidenceGroup,
    EvidenceStatus,
    NormalizedCandidate,
    ScoringConfig,
    Severity,
    SignalResult,
)


def _determine_severity(score: int) -> Severity:
    """Severity bands (after caps): LOW 0-24, MEDIUM 25-49, HIGH 50-74, CRITICAL 75-100."""
    if score >= 75:
        return Severity.CRITICAL
    if score >= 50:
        return Severity.HIGH
    if score >= 25:
        return Severity.MEDIUM
    return Severity.LOW


def _check_category_mismatch(cand_category: str | None, brand_category: str | None, config: ScoringConfig) -> bool:
    """Check category mismatch for apps."""
    if not cand_category or not brand_category:
        return False
    cand_c = cand_category.strip().lower()
    brand_c = brand_category.strip().lower()

    if cand_c == brand_c:
        return False

    synonyms = config.category_synonyms.get(brand_c, [])
    return cand_c not in [s.lower() for s in synonyms]


def assess(
    candidate: NormalizedCandidate | dict[str, Any] | Any,
    brand: BrandCtx | None = None,
    official_assets: Sequence[OfficialAssetCtx] | None = None,
    config: ScoringConfig | None = None,
) -> AssessmentResult:
    """Evaluate candidate asset using IdentityGuard, pure signals, corroboration groups, and gates G1-G5."""
    if candidate is None:
        raise NotImplementedError("Candidate cannot be None (pure assess stub contract).")

    if isinstance(candidate, dict):
        data = dict(candidate)
        data.setdefault("source_id", "demo")
        data.setdefault("stable_identifier", "demo_id")
        if "asset_type" not in data:
            platform = str(data.get("platform", ""))
            if "apple" in platform or "ios" in platform:
                data["asset_type"] = AssetType.IOS_APP
            elif "google" in platform or "android" in platform:
                data["asset_type"] = AssetType.ANDROID_APP
            else:
                data["asset_type"] = AssetType.SOCIAL_ACCOUNT
        candidate = NormalizedCandidate(**data)

    if brand is None:
        brand = BrandCtx(
            id=UUID("acc79881-46b6-4938-8e2d-d10e5acbcb17"),
            name="Kaveri Bank",
            official_domains=["kaveribank.example", "kaveribank.com"],
            distinctive_tokens=["kaveri"],
            demo_brand=True,
        )
    if official_assets is None:
        official_assets = [
            OfficialAssetCtx(
                id=UUID("c0000001-0000-4000-8000-000000000001"),
                brand_id=brand.id,
                asset_type=AssetType.IOS_APP,
                platform="apple_app_store",
                display_name="Kaveri Bank",
                stable_identifier="1234567890",
                developer_id="9000000001",
                publisher_name="Kaveri Bank Ltd",
                secondary_identifiers={"bundle_id": "com.kaveribank.mobile"},
                canonical_url="https://apps.apple.com/in/app/kaveri-bank/id1234567890",
                icon_hash="0000000000000007",
                relationship=Relationship.OFFICIAL,
                trust_publisher=True,
            ),
            OfficialAssetCtx(
                id=UUID("c0000002-0000-4000-8000-000000000002"),
                brand_id=brand.id,
                asset_type=AssetType.SOCIAL_ACCOUNT,
                platform="bluesky",
                display_name="Kaveri Bank",
                stable_identifier="did:plc:kaveriofficial123",
                handle="kaveribank.example",
                canonical_url="https://bsky.app/profile/kaveribank.example",
                icon_hash="0000000000000007",
                relationship=Relationship.OFFICIAL,
                trust_publisher=True,
            ),
            OfficialAssetCtx(
                id=UUID("c0000003-0000-4000-8000-000000000003"),
                brand_id=brand.id,
                asset_type=AssetType.IOS_APP,
                platform="apple_app_store",
                display_name="Kaveri Merchant Connect",
                stable_identifier="1234567899",
                developer_id="9000000099",
                publisher_name="Kaveri Partner Solutions",
                secondary_identifiers={"bundle_id": "com.kaveribank.partner"},
                canonical_url="https://apps.apple.com/in/app/kaveri-merchant/id1234567899",
                icon_hash="0000000000000007",
                relationship=Relationship.AUTHORIZED_PARTNER,
                trust_publisher=True,
            ),
            OfficialAssetCtx(
                id=UUID("c0000004-0000-4000-8000-000000000004"),
                brand_id=brand.id,
                asset_type=AssetType.ANDROID_APP,
                platform="google_play",
                display_name="Kaveri Bank Mobile",
                stable_identifier="com.kaveribank.android",
                developer_id="Kaveri Bank Ltd",
                publisher_name="Kaveri Bank Ltd",
                secondary_identifiers={"package_name": "com.kaveribank.android"},
                canonical_url="https://play.google.com/store/apps/details?id=com.kaveribank.android",
                icon_hash="0000000000000007",
                relationship=Relationship.OFFICIAL,
                trust_publisher=True,
            ),
            OfficialAssetCtx(
                id=UUID("c0000005-0000-4000-8000-000000000005"),
                brand_id=brand.id,
                asset_type=AssetType.IOS_APP,
                platform="apple_app_store",
                display_name="Kaveri Mobile Banking",
                stable_identifier="1456230489",
                developer_id="1378909032",
                icon_hash="0000000000000007",
                canonical_url="https://apps.apple.com/in/app/kaveri/id1456230489",
                relationship=Relationship.OFFICIAL,
                trust_publisher=True,
            ),
            OfficialAssetCtx(
                id=UUID("c0000006-0000-4000-8000-000000000006"),
                brand_id=brand.id,
                asset_type=AssetType.SOCIAL_ACCOUNT,
                platform="bluesky",
                display_name="Kaveri Bank",
                stable_identifier="did:plc:kaveribankofficial",
                handle="kaveribank.bsky.social",
                icon_hash="0000000000000007",
                canonical_url="https://bsky.app/profile/kaveribank.bsky.social",
                relationship=Relationship.OFFICIAL,
                trust_publisher=True,
            ),
        ]
    if config is None:
        config = ScoringConfig()

    scoring_ver = config.scoring_version

    # Step 1: Run IdentityGuard
    id_guard_result = evaluate_identity_guard(candidate, brand, official_assets)
    if id_guard_result is not None:
        return AssessmentResult(
            identity_decision=id_guard_result.decision,
            rule=id_guard_result.rule,
            matched_official_asset_id=id_guard_result.matched_official_asset_id,
            risk_score=None,
            severity=None,
            evidence_coverage=1.0,
            corroborating_groups=[],
            gates_applied=[],
            breakdown=[],
            technique=LookalikeTechnique.NONE,
            nearest_official_asset_id=id_guard_result.matched_official_asset_id,
            explanation=id_guard_result.explanation,
            scoring_version=scoring_ver,
            relevant=True,
        )

    # Step 2: Calculate name_similarity and technique
    if candidate.asset_type == AssetType.SOCIAL_ACCOUNT:
        name_res = calculate_social_name_similarity(
            official_name=brand.name,
            display_name=candidate.display_name,
            handle=candidate.handle,
            distinctive_tokens=brand.distinctive_tokens,
            generic_tokens_extra=brand.generic_tokens_extra,
        )
    else:
        name_res = calculate_name_similarity(
            official_name=brand.name,
            candidate_name=candidate.display_name,
            distinctive_tokens=brand.distinctive_tokens,
            generic_tokens_extra=brand.generic_tokens_extra,
        )

    name_sim = name_res.name_similarity

    # Classify technique
    technique, _ = classify_technique(
        observed=candidate.display_name or candidate.handle or "",
        official=brand.name,
    )

    # Find nearest official asset (if any)
    nearest_asset_id = official_assets[0].id if official_assets else None

    # Gate G1: Relevance
    # if name_similarity < 0.60 -> relevant = False (fails G1)
    if name_sim < config.relevance_threshold:
        return AssessmentResult(
            identity_decision=IdentityDecision.BELOW_THRESHOLD,
            rule="G1_NOT_RELEVANT",
            matched_official_asset_id=None,
            risk_score=None,
            severity=None,
            evidence_coverage=None,
            corroborating_groups=[],
            gates_applied=["G1_RELEVANCE"],
            breakdown=[],
            technique=technique,
            nearest_official_asset_id=nearest_asset_id,
            explanation="Not relevant: name similarity below threshold 0.60.",
            scoring_version=scoring_ver,
            relevant=False,
        )

    # Step 3: Calculate signals and evidence coverage
    if candidate.asset_type == AssetType.SOCIAL_ACCOUNT:
        breakdown, evidence_coverage = evaluate_social_signals(candidate, brand, official_assets, name_sim)
    else:
        breakdown, evidence_coverage = evaluate_app_signals(candidate, brand, official_assets, name_sim)

    # Calculate corroborating groups:
    # Groups: NAME, IDENTITY, VISUAL, CONTENT, CONTEXT.
    # A group fires when any of its signals has v >= 0.5 and status OBSERVED.
    # corroborating_groups = fired groups EXCLUDING NAME.
    fired_groups: set[EvidenceGroup] = set()
    for sig in breakdown:
        if sig.value >= 0.5 and sig.status == EvidenceStatus.OBSERVED:
            fired_groups.add(sig.group)

    corroborating_groups: list[EvidenceGroup] = [g for g in fired_groups if g != EvidenceGroup.NAME]

    # Raw points sum
    raw_points_sum = sum(sig.points for sig in breakdown)
    score = round(raw_points_sum)

    gates_applied: list[str] = []
    decision: IdentityDecision | None = None
    rule: str = ""
    explanation: str = ""

    # Helper signal lookups
    signal_map: dict[str, SignalResult] = {s.signal: s for s in breakdown}
    desc_sim_val = signal_map.get("description_similarity", signal_map.get("bio_similarity"))
    desc_c = desc_sim_val.detail.get("cosine", 0.0) if desc_sim_val else 0.0

    # Step 4: Gate G4 Benign lookalike
    # corroborating_groups == 0 and (category mismatch or observed description/bio similarity < 0.20)
    cat_mismatch = (
        _check_category_mismatch(candidate.category, brand.industry_category, config)
        if candidate.asset_type != AssetType.SOCIAL_ACCOUNT
        else False
    )
    low_content_overlap = (desc_sim_val is not None and desc_sim_val.status == EvidenceStatus.OBSERVED and desc_c < 0.20)

    if len(corroborating_groups) == 0 and (cat_mismatch or low_content_overlap):
        decision = IdentityDecision.BENIGN_LOOKALIKE
        if cat_mismatch:
            rule = "G4_UNRELATED_CATEGORY"
            explanation = "Similar name, unrelated category, no corroborating evidence."
        else:
            rule = "G4_LOW_CONTENT_OVERLAP"
            explanation = "Similar name, low content overlap, no corroborating evidence."
        gates_applied.append("G4_BENIGN_LOOKALIKE")
        score = min(score, 24)

    # Step 5: Gate G5 Declared unofficial (Section 8.4a)
    # Applies if G4 did not trigger, and ALL 4 safeguards hold:
    # 1. Disclaimer term in bio or description (not name/handle)
    # 2. lure_terms v == 0, and no external link points outside official domains
    # 3. No VISUAL or IDENTITY group fired
    # 4. Technique is NOT EXACT_NAME_REUSE or HOMOGLYPH
    if decision is None:
        cand_bio = candidate.description or ""
        disclaimer_hits = count_lexicon_hits(cand_bio, DISCLAIMER_TERMS)
        has_bio_disclaimer = len(disclaimer_hits) > 0

        lure_sig = signal_map.get("lure_terms")
        lure_v = lure_sig.value if lure_sig else 0.0

        # External links: all must be in official domains (or empty)
        official_domains = {d.lower() for d in brand.official_domains if d}
        mismatching_link = False
        if candidate.external_links:
            mismatching_link = any(not any(d in extract_domain(l) for d in official_domains) for l in candidate.external_links)

        visual_or_identity_fired = (EvidenceGroup.VISUAL in fired_groups) or (EvidenceGroup.IDENTITY in fired_groups)
        is_exact_or_homoglyph = technique in (LookalikeTechnique.EXACT_NAME_REUSE, LookalikeTechnique.HOMOGLYPH)

        if (
            has_bio_disclaimer
            and lure_v == 0.0
            and not mismatching_link
            and not visual_or_identity_fired
            and not is_exact_or_homoglyph
        ):
            decision = IdentityDecision.BENIGN_LOOKALIKE
            rule = "G5_DECLARED_UNOFFICIAL"
            explanation = "Declared unofficial in bio. Not verified. Disclaimers can be copied by impersonators; an analyst may reopen this."
            gates_applied.append("G5_DECLARED_UNOFFICIAL")
            score = min(score, 24)
        elif has_bio_disclaimer and visual_or_identity_fired:
            gates_applied.append("G5_OVERRIDDEN_BY_COPY")
        elif has_bio_disclaimer and (lure_v > 0.0 or mismatching_link):
            gates_applied.append("G5_OVERRIDDEN_BY_LURE_OR_LINK")
        elif has_bio_disclaimer and is_exact_or_homoglyph:
            gates_applied.append("G5_OVERRIDDEN_BY_EXACT_NAME")

    # Step 6: Gate G2 Corroboration
    # If len(corroborating_groups) < 2 -> cap score at 49 (max MEDIUM)
    if len(corroborating_groups) < 2 and decision is None and score > 49:
        score = 49
        gates_applied.append("G2_CORROBORATION")

    # Step 7: Gate G3 Coverage
    # If evidence_coverage < 0.50 -> cap score at 49 and add note
    if evidence_coverage < 0.50 and decision is None:
        score = min(score, 49)
        gates_applied.append("G3_COVERAGE")

    # Step 8: Threshold check
    final_score = max(0, min(100, score))

    if decision is None:
        if final_score < config.review_threshold:
            decision = IdentityDecision.BELOW_THRESHOLD
            rule = "BELOW_REVIEW_THRESHOLD"
            explanation = f"Risk score ({final_score}) below review threshold ({config.review_threshold})."
        else:
            decision = IdentityDecision.CANDIDATE_FOR_REVIEW
            rule = "CANDIDATE_FOR_REVIEW"
            exp_parts = ["Candidate for review: similar name"]
            if EvidenceGroup.VISUAL in corroborating_groups:
                exp_parts.append("matching icon/avatar")
            if EvidenceGroup.CONTENT in corroborating_groups:
                exp_parts.append("overlapping content/lures")
            if EvidenceGroup.CONTEXT in corroborating_groups:
                exp_parts.append("suspicious link or thin footprint")
            explanation = ", ".join(exp_parts) + ". Signals observed; not proof of malicious intent."
            if "G3_COVERAGE" in gates_applied:
                explanation += " Insufficient evidence."

    severity = _determine_severity(final_score)

    return AssessmentResult(
        identity_decision=decision,
        rule=rule,
        matched_official_asset_id=None,
        risk_score=final_score,
        severity=severity,
        evidence_coverage=evidence_coverage,
        corroborating_groups=corroborating_groups,
        gates_applied=gates_applied,
        breakdown=breakdown,
        technique=technique,
        nearest_official_asset_id=nearest_asset_id,
        explanation=explanation,
        scoring_version=scoring_ver,
        relevant=True,
    )
