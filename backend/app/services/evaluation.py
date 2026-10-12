"""Offline evaluation harness for ThreatLens v3 per Sections 11.6 and 14.

Pure deterministic logic: zero network calls, zero database operations.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from backend.app.services.assess.engine import assess
from backend.app.services.normalization.name_similarity import calculate_name_similarity
from backend.app.services.query_planner.models import (
    BrandCtx,
    IdentityDecision,
    OfficialAssetCtx,
)
from backend.app.services.scoring.models import NormalizedCandidate, ScoringConfig

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "eval" / "datasets"


def wilson_95_interval(k: int, n: int) -> list[float]:
    """Calculate Wilson 95% score confidence interval for k successes out of n trials.

    Formula from Section 14:
    p = k / n, z = 1.96
    centre = (p + z^2 / (2n)) / (1 + z^2 / n)
    half = z * sqrt(p*(1-p)/n + z^2/(4*n^2)) / (1 + z^2 / n)
    clamped to [0.0, 1.0].
    """
    if n <= 0:
        return [0.0, 1.0]

    p = k / n
    z = 1.96
    z2 = z * z
    denom = 1.0 + z2 / n

    centre = (p + z2 / (2.0 * n)) / denom
    inside_sqrt = (p * (1.0 - p) / n) + (z2 / (4.0 * n * n))
    half = (z * math.sqrt(max(0.0, inside_sqrt))) / denom

    low = max(0.0, min(1.0, round(centre - half, 2)))
    high = max(0.0, min(1.0, round(centre + half, 2)))
    return [low, high]


def load_dataset(dataset_id: str = "threatlens-v1") -> tuple[BrandCtx, list[OfficialAssetCtx], list[dict[str, Any]]]:
    """Load dataset brand, official assets, and cases offline from JSON/JSONL files."""
    ds_path = DATASETS_DIR / dataset_id
    if not ds_path.exists():
        raise FileNotFoundError(f"Dataset {dataset_id} not found at {ds_path}")

    brand_file = ds_path / "brand.json"
    with open(brand_file, "r", encoding="utf-8") as f:
        brand_data = json.load(f)

    brand = BrandCtx(**brand_data["brand"])
    official_assets = [OfficialAssetCtx(**a) for a in brand_data["official_assets"]]

    cases = []
    cases_file = ds_path / "cases.jsonl"
    with open(cases_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    return brand, official_assets, cases


def run_assessment_ablation(
    candidate: NormalizedCandidate,
    brand: BrandCtx,
    official_assets: list[OfficialAssetCtx],
    config: ScoringConfig,
    ablation: str = "FULL",
) -> Any:
    """Run assess() with an ablation configuration:
    - FULL: standard assess() pipeline
    - NO_IDENTITYGUARD: empty official assets list (bypasses R1-R3)
    - NO_GATES: raw score >= 25 without G1-G5 caps
    - NO_ICON: candidate icon_hash forced to None (UNAVAILABLE)
    - NO_DESCRIPTION: candidate description forced to None (UNAVAILABLE)
    """
    cand = candidate.model_copy(deep=True)

    if ablation == "NO_IDENTITYGUARD":
        return assess(cand, brand, [], config)
    elif ablation == "NO_ICON":
        cand.icon_hash = None
        return assess(cand, brand, official_assets, config)
    elif ablation == "NO_DESCRIPTION":
        cand.description = None
        return assess(cand, brand, official_assets, config)
    elif ablation == "NO_GATES":
        # Bypass G1-G5 gates: evaluate IdentityGuard, then check if raw points >= 25
        res = assess(cand, brand, official_assets, config)
        if res.identity_decision in (
            IdentityDecision.OFFICIAL_EXACT_MATCH,
            IdentityDecision.OFFICIAL_PUBLISHER_MATCH,
            IdentityDecision.AUTHORIZED_PARTNER_MATCH,
        ):
            return res
        # Uncapped raw score sum
        raw_score = sum(s.points for s in res.breakdown) if res.breakdown else (res.risk_score or 0)
        new_dec = IdentityDecision.CANDIDATE_FOR_REVIEW if raw_score >= 25 else IdentityDecision.BELOW_THRESHOLD
        return res.model_copy(update={"identity_decision": new_dec, "risk_score": round(raw_score)})

    return assess(cand, brand, official_assets, config)


def tune_baseline_on_dev(dev_cases: list[dict[str, Any]], brand: BrandCtx) -> float:
    """Find threshold t in [0.50, 0.95] that maximizes F1 on DEV split (ties -> higher precision)."""
    best_t = 0.80
    best_f1 = -1.0
    best_p = -1.0

    # Test potential thresholds
    for step in range(50, 96, 5):
        t = step / 100.0
        tp, fp, fn = 0, 0, 0
        for c in dev_cases:
            is_pos = (c["label"] == "IMPERSONATION")
            cand_name = c["candidate"].get("display_name", "")
            sim = calculate_name_similarity(brand.name, cand_name).name_similarity
            pred_pos = (sim >= t)

            if is_pos and pred_pos:
                tp += 1
            elif not is_pos and pred_pos:
                fp += 1
            elif is_pos and not pred_pos:
                fn += 1

        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

        if f1 > best_f1 or (f1 == best_f1 and p > best_p):
            best_f1 = f1
            best_p = p
            best_t = t

    return best_t


def evaluate_dataset(
    dataset_id: str = "threatlens-v1",
    split: Literal["DEV", "HELDOUT"] = "HELDOUT",
    include_baseline: bool = True,
    include_ablation: bool = True,
    config: ScoringConfig | None = None,
) -> dict[str, Any]:
    """Offline deterministic evaluation harness matching Section 11.6 and Section 14."""
    if config is None:
        config = ScoringConfig()

    brand, official_assets, all_cases = load_dataset(dataset_id)

    target_cases = [c for c in all_cases if c["split"] == split]
    dev_cases = [c for c in all_cases if c["split"] == "DEV"]

    # Tune baseline on DEV split
    baseline_threshold = tune_baseline_on_dev(dev_cases, brand)

    tp, fp, tn, fn = 0, 0, 0, 0
    official_flagged_count = 0
    hard_negatives_tested = 0
    hard_negatives_cleared = 0

    technique_stats: dict[str, dict[str, int]] = {}
    failure_cases = []

    for c in target_cases:
        label = c["label"]
        cand = NormalizedCandidate(**c["candidate"])
        res = assess(cand, brand, official_assets, config)

        is_actual_pos = (label == "IMPERSONATION")
        is_pred_pos = (res.identity_decision == IdentityDecision.CANDIDATE_FOR_REVIEW)

        # Official flagged count (must strictly equal 0)
        if label == "OFFICIAL" and is_pred_pos:
            official_flagged_count += 1

        # Hard negatives (BENIGN_NAMESAKE)
        if label == "BENIGN_NAMESAKE":
            hard_negatives_tested += 1
            if not is_pred_pos:
                hard_negatives_cleared += 1

        # Confusion counts
        if is_actual_pos and is_pred_pos:
            tp += 1
        elif not is_actual_pos and is_pred_pos:
            fp += 1
        elif not is_actual_pos and not is_pred_pos:
            tn += 1
        else:
            fn += 1

        # Technique recall tracking
        if is_actual_pos:
            tech = c.get("technique") or "UNKNOWN"
            if tech not in technique_stats:
                technique_stats[tech] = {"tested": 0, "detected": 0}
            technique_stats[tech]["tested"] += 1
            if is_pred_pos:
                technique_stats[tech]["detected"] += 1

        # Failure cases tracking
        if (is_actual_pos and not is_pred_pos) or (not is_actual_pos and is_pred_pos):
            failure_cases.append({
                "case_id": c["case_id"],
                "expected": label,
                "got": res.identity_decision.value,
                "why": res.explanation,
            })

    # Metric computations
    precision = round(tp / (tp + fp), 2) if (tp + fp) > 0 else None
    recall = round(tp / (tp + fn), 2) if (tp + fn) > 0 else None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = round((2.0 * precision * recall) / (precision + recall), 2)
    else:
        f1 = None
    fpr = round(fp / (fp + tn), 2) if (fp + tn) > 0 else 0.0

    # Wilson 95% intervals
    p_ci = wilson_95_interval(tp, tp + fp) if (tp + fp) > 0 else [0.0, 1.0]
    r_ci = wilson_95_interval(tp, tp + fn) if (tp + fn) > 0 else [0.0, 1.0]
    fpr_ci = wilson_95_interval(fp, fp + tn) if (fp + tn) > 0 else [0.0, 1.0]

    technique_recall_list = [
        {"technique": tech, "tested": stats["tested"], "detected": stats["detected"]}
        for tech, stats in sorted(technique_stats.items())
    ]

    result: dict[str, Any] = {
        "id": str(uuid4()),
        "dataset_id": dataset_id,
        "split": split,
        "scoring_version": config.scoring_version,
        "threshold": {"review": config.review_threshold},
        "sample_count": len(target_cases),
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fpr,
        "confidence_intervals": {
            "precision": p_ci,
            "recall": r_ci,
            "false_positive_rate": fpr_ci,
            "method": "wilson_95",
        },
        "official_flagged_count": official_flagged_count,
        "hard_negatives": {
            "tested": hard_negatives_tested,
            "correctly_cleared": hard_negatives_cleared,
            "false_positives": hard_negatives_tested - hard_negatives_cleared,
        },
        "technique_recall": technique_recall_list,
        "failure_cases": failure_cases,
        "definitions": "Positive class = IMPERSONATION. Predicted positive = decision CANDIDATE_FOR_REVIEW. OFFICIAL cases count as negatives and any flagged official asset is also reported separately.",
        "limitations": ["Positives are synthetic.", "Negatives are real captured namesakes labelled by the team."],
    }

    # Baseline evaluation on the same split
    if include_baseline:
        b_tp, b_fp, b_tn, b_fn = 0, 0, 0, 0
        for c in target_cases:
            is_pos = (c["label"] == "IMPERSONATION")
            cand_name = c["candidate"].get("display_name", "")
            sim = calculate_name_similarity(brand.name, cand_name).name_similarity
            pred_pos = (sim >= baseline_threshold)
            if is_pos and pred_pos:
                b_tp += 1
            elif not is_pos and pred_pos:
                b_fp += 1
            elif not is_pos and not pred_pos:
                b_tn += 1
            else:
                b_fn += 1

        b_p = round(b_tp / (b_tp + b_fp), 2) if (b_tp + b_fp) > 0 else 0.0
        b_r = round(b_tp / (b_tp + b_fn), 2) if (b_tp + b_fn) > 0 else 0.0
        b_fpr = round(b_fp / (b_fp + b_tn), 2) if (b_fp + b_tn) > 0 else 0.0

        result["baseline"] = {
            "name": "name_only_rapidfuzz",
            "tuned_on": "DEV",
            "threshold": baseline_threshold,
            "precision": b_p,
            "recall": b_r,
            "false_positive_rate": b_fpr,
        }

    # Ablation suite
    if include_ablation:
        ablations_to_run = ["FULL", "NO_IDENTITYGUARD", "NO_GATES", "NO_ICON", "NO_DESCRIPTION"]
        ablation_rows = []

        for abl in ablations_to_run:
            a_tp, a_fp, a_fn = 0, 0, 0
            a_official_flagged = 0
            for c in target_cases:
                label = c["label"]
                cand = NormalizedCandidate(**c["candidate"])
                a_res = run_assessment_ablation(cand, brand, official_assets, config, ablation=abl)
                is_actual_pos = (label == "IMPERSONATION")
                is_pred_pos = (a_res.identity_decision == IdentityDecision.CANDIDATE_FOR_REVIEW)

                if label == "OFFICIAL" and is_pred_pos:
                    a_official_flagged += 1

                if is_actual_pos and is_pred_pos:
                    a_tp += 1
                elif not is_actual_pos and is_pred_pos:
                    a_fp += 1
                elif is_actual_pos and not is_pred_pos:
                    a_fn += 1

            a_p = round(a_tp / (a_tp + a_fp), 2) if (a_tp + a_fp) > 0 else 0.0
            a_r = round(a_tp / (a_tp + a_fn), 2) if (a_tp + a_fn) > 0 else 0.0
            row: dict[str, Any] = {
                "configuration": abl,
                "precision": a_p,
                "recall": a_r,
            }
            if abl == "NO_IDENTITYGUARD":
                row["official_flagged_count"] = a_official_flagged
            ablation_rows.append(row)

        result["ablation"] = ablation_rows

    return result
