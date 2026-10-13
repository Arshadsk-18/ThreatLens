"""Unit tests for offline evaluation harness and threatlens-v1 dataset per Section 11.6 and Section 14."""


from backend.app.services.evaluation import (
    evaluate_dataset,
    load_dataset,
    wilson_95_interval,
)


def test_dataset_composition():
    """Verify threatlens-v1 dataset has exactly 192 cases (120 baseline + 72 Person 3 verified negatives)."""
    brand, official_assets, cases = load_dataset("threatlens-v1")
    assert brand.name == "Kaveri Bank"
    assert len(official_assets) == 3
    assert len(cases) == 192

    dev_count = sum(1 for c in cases if c["split"] == "DEV")
    heldout_count = sum(1 for c in cases if c["split"] == "HELDOUT")
    assert dev_count == 115
    assert heldout_count == 77

    impersonation_count = sum(1 for c in cases if c["label"] == "IMPERSONATION")
    namesake_count = sum(1 for c in cases if c["label"] == "BENIGN_NAMESAKE")
    official_count = sum(1 for c in cases if c["label"] == "OFFICIAL")
    assert impersonation_count == 40
    assert namesake_count == 132
    assert official_count == 20


def test_wilson_interval():
    """Validate mathematical correctness of Wilson 95% confidence intervals against known properties."""
    # Extreme cases: 0 of 10
    interval_zero = wilson_95_interval(0, 10)
    assert interval_zero[0] == 0.0
    assert interval_zero[1] > 0.0
    assert interval_zero[1] <= 0.35

    # 10 of 10
    interval_full = wilson_95_interval(10, 10)
    assert interval_full[0] >= 0.65
    assert interval_full[1] == 1.0

    # 50 of 100
    interval_half = wilson_95_interval(50, 100)
    assert 0.38 <= interval_half[0] <= 0.42
    assert 0.58 <= interval_half[1] <= 0.62

    # Denominator zero edge case
    interval_empty = wilson_95_interval(0, 0)
    assert interval_empty == [0.0, 1.0]


def test_official_flagged_count_zero():
    """Must-pass automated test: official assets are never flagged in evaluation (official_flagged_count == 0)."""
    dev_results = evaluate_dataset("threatlens-v1", split="DEV")
    assert dev_results["official_flagged_count"] == 0, "Official asset was flagged in DEV split!"

    heldout_results = evaluate_dataset("threatlens-v1", split="HELDOUT")
    assert heldout_results["official_flagged_count"] == 0, "Official asset was flagged in HELDOUT split!"


def test_eval_metrics_computed_not_hardcoded():
    """Verify evaluation harness dynamically calculates confusion matrix, precision, recall, F1, and intervals."""
    res = evaluate_dataset("threatlens-v1", split="HELDOUT", include_baseline=True, include_ablation=True)

    # Check structure
    assert res["dataset_id"] == "threatlens-v1"
    assert res["split"] == "HELDOUT"
    assert res["sample_count"] == 77

    # Confusion matrix sum
    conf = res["confusion"]
    total = conf["tp"] + conf["fp"] + conf["tn"] + conf["fn"]
    assert total == 77

    # Mathematical consistency
    if conf["tp"] + conf["fp"] > 0:
        expected_p = round(conf["tp"] / (conf["tp"] + conf["fp"]), 2)
        assert res["precision"] == expected_p

    if conf["tp"] + conf["fn"] > 0:
        expected_r = round(conf["tp"] / (conf["tp"] + conf["fn"]), 2)
        assert res["recall"] == expected_r

    # High performance on HELDOUT
    assert res["recall"] >= 0.85
    assert res["precision"] >= 0.85
    assert res["false_positive_rate"] <= 0.10

    # Hard negatives verified
    hn = res["hard_negatives"]
    assert hn["tested"] == 53
    assert hn["correctly_cleared"] >= 50

    # Baseline and ablations present
    assert "baseline" in res
    assert res["baseline"]["name"] == "name_only_rapidfuzz"
    assert "ablation" in res
    ablation_configs = {a["configuration"] for a in res["ablation"]}
    assert {"FULL", "NO_IDENTITYGUARD", "NO_GATES", "NO_ICON", "NO_DESCRIPTION"}.issubset(ablation_configs)

    # Without IdentityGuard, official assets get flagged
    no_idg = next(a for a in res["ablation"] if a["configuration"] == "NO_IDENTITYGUARD")
    assert no_idg.get("official_flagged_count", 0) > 0


def test_person3_hard_negatives_clearance():
    """Verify that all 72 Person 3 real negative records are cleared (BENIGN_LOOKALIKE or BELOW_THRESHOLD)."""
    import json
    from pathlib import Path

    from backend.app.services.assess.engine import assess
    from backend.app.services.query_planner.models import IdentityDecision
    from backend.app.services.scoring.models import NormalizedCandidate, ScoringConfig

    brand, official_assets, _ = load_dataset("threatlens-v1")
    config = ScoringConfig()

    fixture_path = Path(__file__).parent / "fixtures" / "real_negatives" / "verified.jsonl"
    if not fixture_path.exists():
        fixture_path = Path("backend/tests/fixtures/real_negatives/verified.jsonl")
    assert fixture_path.exists(), f"Delivery fixture {fixture_path} not found!"

    with open(fixture_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    assert len(records) == 72, f"Expected 72 records, got {len(records)}"

    flagged = []
    for r in records:
        assert r["provenance"] == "REAL_CAPTURED"
        assert "analyst_alpha" in r["labeler"] and "analyst_beta" in r["labeler"]
        cand = NormalizedCandidate(**r["candidate"])
        res = assess(cand, brand, official_assets, config)

        assert res.identity_decision in (
            IdentityDecision.BENIGN_LOOKALIKE,
            IdentityDecision.BELOW_THRESHOLD,
        ), f"Record {r['id']} ({cand.display_name}) incorrectly classified as {res.identity_decision}!"

        if res.identity_decision == IdentityDecision.CANDIDATE_FOR_REVIEW:
            flagged.append(r["id"])

    assert len(flagged) == 0, f"Expected 0 flagged hard negatives, found {len(flagged)}"

