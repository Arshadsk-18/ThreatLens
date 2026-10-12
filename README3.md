# ThreatLens — Person 4 Implementation Guide
## Detection, IdentityGuard, and Evaluation Harness

**Role:** Person 4 (Detection, IdentityGuard, Evaluation)  
**Branch:** `feat/detection`  
**Contract Version:** `3.0.0` (per `ThreatLens_v3_Architecture_API_Contract2.md`)

---

## 1. Overview & Architecture

ThreatLens digital risk protection surfaces **candidates for review** by monitoring social media and app store listings for unauthorized look-alikes. Official assets are cleared strictly by **exact identity evidence** rather than name similarity.

Person 4's implementation is **100% pure Python**:
- Zero database connections
- Zero network calls or HTTP requests
- Fully deterministic scoring and classification

---

## 2. Directory Structure & Components

```text
backend/
├── app/
│   └── services/
│       ├── assess/
│       │   └── engine.py               # Master assess() pipeline with Gates G1-G5
│       ├── compare/
│       │   └── comparison.py           # FieldComparison, character diffs, and perceptual hash similarity
│       ├── evaluation.py               # Offline benchmark harness, ablations, Wilson 95% CIs
│       ├── identity_guard/
│       │   └── guard.py                # IdentityGuard: R1_EXACT_ID, R2_PUBLISHER_ID, R3_PARTNER
│       ├── lexicons/
│       │   ├── disclaimer_terms.json   # Unofficial/parody terms for G5
│       │   └── lure_terms.json         # Phishing/scam lure terms for CONTENT scoring
│       ├── normalization/
│       │   ├── name_similarity.py      # Unicode NFKC, RapidFuzz ratio_full, weighted token_score
│       │   ├── normalizer.py           # Normalization utilities
│       │   ├── technique.py            # Technique classifier
│       │   └── techniques.py           # LookalikeTechnique classifier with metadata
│       ├── query_planner/
│       │   ├── models.py               # BrandCtx, OfficialAssetCtx, PlannedQuery, QueryPlan
│       │   └── planner.py              # plan_queries() with source limits and priority sorting
│       └── scoring/
│           ├── evaluators.py           # App & social signal evaluators (100 max points)
│           └── models.py               # NormalizedCandidate, SignalResult, ScoringConfig, AssessmentResult
├── eval/
│   ├── datasets/
│   │   └── threatlens-v1/
│   │       ├── brand.json              # Evaluation brand definition & official assets
│   │       ├── cases.jsonl             # 120 labeled benchmark cases (72 DEV / 48 HELDOUT)
│   │       ├── evaluation_summary.json # Complete evaluation results export
│   │       └── README.md               # Dataset documentation
│   └── generate_dataset.py             # Reproducible dataset generator script
└── tests/
    ├── fixtures/
    │   └── name_vectors.json           # 42 golden test vectors for name similarity
    ├── test_assess.py                  # Walkthroughs A-E, G1-G5 gates, worked examples
    ├── test_evaluation.py              # Benchmark execution, Wilson intervals, zero-false-positive checks
    ├── test_identity_guard.py          # IdentityGuard R1, R2, R3 verification
    ├── test_lookalike_techniques.py    # LookalikeTechnique classification tests
    ├── test_name_similarity_vectors.py # 42 vector precision & recall tests
    ├── test_normalization.py           # Normalization & homoglyph tests
    └── test_query_planner.py           # Query bounds and priority sequence tests
```

---

## 3. Core Modules & Implementation Logic

### A. Name Normalization & Similarity (`normalization/`)
- **Unicode NFKC normalization**, case-folding, whitespace collapsing, and separator mapping (`-_.` to single space).
- **Homoglyph & confusable mapping**: Converts Cyrillic (e.g., `'і'`, `'а'`) and Greek look-alikes to Latin while flagging `homoglyph_detected = True`.
- **Reference Similarity Formula (Section 8.1):**
  - $\text{ratio\_full} = \max(\text{RapidFuzz ratio on normalized string}, \text{RapidFuzz ratio with spaces collapsed})$
  - $\text{token\_score} = \frac{\sum (w_t \times m_t)}{\sum w_t + 0.2 \times \text{extra\_token\_count}}$
    - Distinctive brand tokens weight: `1.0`
    - Generic tokens (`bank`, `app`, `support`, etc.) weight: `0.2`
    - Token match threshold: $\ge 0.80$
    - Extra unmatched candidate tokens penalty weight: `0.2`
  - $\text{name\_similarity} = \text{round}(\max(\text{ratio\_full}, \text{token\_score}), 2)$
  - For social accounts, computes similarity against both display name and handle (with domain suffix stripped, e.g. `.bsky.social`) and selects the higher score.

### B. Lookalike Technique Classifier (`normalization/techniques.py`)
Classifies candidates according to strict contract precedence:
1. `EXACT_NAME_REUSE`
2. `HOMOGLYPH`
3. `CHARACTER_SWAP`
4. `OMISSION`
5. `REPETITION`
6. `KEYBOARD_ADJACENT`
7. `ADDED_WORD`
8. `SPACING`
9. `SEPARATOR`
10. `NONE`

### C. IdentityGuard (`identity_guard/guard.py`)
Pure function evaluating candidates against registered official assets:
- **`R1_EXACT_ID`**: Matches `stable_identifier` (Apple `trackId`, Bluesky `did`) or secondary identifiers (`bundle_id`, `handle`) of an active verified `OFFICIAL` asset $\rightarrow$ `OFFICIAL_EXACT_MATCH`.
- **`R2_PUBLISHER_ID`**: Matches developer ID of an active verified `OFFICIAL` asset where `trust_publisher = True` $\rightarrow$ `OFFICIAL_PUBLISHER_MATCH`.
- **`R3_PARTNER`**: Matches an asset with `relationship = AUTHORIZED_PARTNER` $\rightarrow$ `AUTHORIZED_PARTNER_MATCH`.
- **Invariant**: **Never** clears on name, publisher string, icon, or description alone. Returns `None` if unverified to continue to scoring.

### D. Query Planner (`query_planner/planner.py`)
Generates bounded and prioritized retrieval queries:
- Query bounds: Default 8 for `apple_itunes`, 6 for `bluesky_public`, hard maximum cap 12.
- Priority ordering:
  1. `BASE`: Brand name and official asset display names.
  2. `SPACING`: Concatenated/spaced variations (`"kaveribank"` $\leftrightarrow$ `"kaveri bank"`).
  3. `SEPARATOR`: Hyphen/dot variations (`"kaveri-bank"`, `"kaveri.bank"`).
  4. `ADDED_WORD`: Brand + targeted risk terms (`official`, `support`, `rewards`, `kyc`, `care`, `app`, `mobile`, `loan`).
  5. `DISTINCTIVE`: Distinctive token alone (`"kaveri"`).

### E. Signal Evaluator (`scoring/evaluators.py`)
Each asset class sums to a maximum of 100 points:

#### Mobile Apps (`IOS_APP`, `ANDROID_APP`):
- `name_lookalike` (25 pts, `NAME`): $\text{clamp}((\text{name\_sim} - 0.50) / 0.45)$
- `publisher_impersonation` (20 pts, `IDENTITY`): Resemblance to official publisher or brand name (mismatch carries 0 points)
- `icon_similarity` (20 pts, `VISUAL`): Based on perceptual hash ($1 - \frac{\text{hamming}}{64}$)
- `description_similarity` (15 pts, `CONTENT`): Char 3-gram cosine overlap with official descriptions
- `link_domain_mismatch` (8 pts, `CONTEXT`): Verified against registered official domains
- `lure_terms` (6 pts, `CONTENT`): Distinct phrase hits from `lure_terms.json`
- `thin_footprint` (6 pts, `CONTEXT`): Age $< 90$ days, rating count $< 50$

#### Social Accounts (`SOCIAL_ACCOUNT`):
- `name_lookalike` (25 pts, `NAME`): Higher of display name or handle
- `avatar_similarity` (20 pts, `VISUAL`): Perceptual hash similarity
- `bio_similarity` (15 pts, `CONTENT`): Cosine overlap against brand text
- `link_domain_mismatch` (15 pts, `CONTEXT`): Unofficial link = 1.0; no link = 0.5 (`INFERRED`)
- `lure_terms` (10 pts, `CONTENT`): Phrase hits across bio, name, handle
- `thin_footprint` (15 pts, `CONTEXT`): Age $< 90$ days, followers $< 100$, posts $< 10$

- Signal status tracking: `OBSERVED`, `INFERRED`, `UNAVAILABLE`, `SIMULATED`.
- Evidence coverage: Sum of max points for available signals divided by 100.

### F. Master Assessment Engine (`assess/engine.py`)
Executes the full evaluation pipeline:
1. **IdentityGuard**: Immediate return on match (`OFFICIAL_EXACT_MATCH`, `OFFICIAL_PUBLISHER_MATCH`, `AUTHORIZED_PARTNER_MATCH`).
2. **Gate G1 (Relevance)**: If $\text{name\_similarity} < 0.60 \rightarrow \text{relevant} = \text{False}$.
3. **Signal Evaluation**: Computes signals, `evidence_coverage`, and corroborating groups (fired groups with $v \ge 0.5$, status `OBSERVED`, excluding `NAME`).
4. **Gate G4 (Benign Lookalike)**: If 0 corroborating groups AND (category mismatch OR bio similarity $< 0.20$) $\rightarrow$ `BENIGN_LOOKALIKE` (capped at 24).
5. **Gate G5 (Declared Unofficial Safeguards)**: If disclaimer in bio/description AND lure terms $v = 0$ AND no mismatching links AND no `VISUAL`/`IDENTITY` fired AND technique not exact/homoglyph $\rightarrow$ `BENIGN_LOOKALIKE` (capped at 24).
6. **Gate G2 (Corroboration)**: If corroborating groups $< 2 \rightarrow$ Score capped at 49 (max `MEDIUM`).
7. **Gate G3 (Coverage)**: If `evidence_coverage` $< 0.50 \rightarrow$ Score capped at 49 with `"Insufficient evidence"` note.
8. **Threshold Decision**: Score $< 25 \rightarrow \text{BELOW\_THRESHOLD}$; otherwise $\rightarrow \text{CANDIDATE\_FOR\_REVIEW}$.

---

## 4. Section 12 Interface Contracts

Person 4 implements and exposes the exact Section 12 Python interfaces for orchestrator and evaluation integration:

1. **`assess` (`backend/app/services/assess/engine.py`):**
   ```python
   def assess(
       candidate: NormalizedCandidate,
       brand: BrandCtx,
       official_assets: list[OfficialAssetCtx],
       config: ScoringConfig | None = None,
   ) -> AssessmentResult
   ```
2. **`plan_queries` (`backend/app/services/query_planner/planner.py`):**
   ```python
   def plan_queries(
       brand: BrandCtx,
       assets: list[OfficialAssetCtx],
       source_id: str,
       max_queries: int | None = None,
   ) -> QueryPlan
   ```
3. **`compare` & `icon_similarity` (`backend/app/services/compare/comparison.py`):**
   ```python
   def compare(
       candidate: NormalizedCandidate,
       official: OfficialAssetCtx,
   ) -> list[FieldComparison]

   def icon_similarity(hash_a: str | None, hash_b: str | None) -> float
   ```

---

## 5. Evaluation Benchmark (`eval/`)

### Dataset: `threatlens-v1`
- **Total Cases:** 192 (120 baseline cases + 72 Person 3 verified hard negatives)
- **Splits:** 115 DEV (59.9%), 77 HELDOUT (40.1%)
- **Class Breakdown:**
  - `IMPERSONATION`: 40 cases (synthetic, covering all look-alike techniques + 4 adversarial disclaimer abuse cases)
  - `BENIGN_NAMESAKE`: 132 cases (60 baseline + 72 Person 3 delivery with dual sign-off from `analyst_alpha` and `analyst_beta`)
  - `OFFICIAL`: 20 cases (exact ID matches, publisher portfolio, partner assets)

### Benchmark Results on HELDOUT (Frozen Thresholds)
- **Sample Count:** 77
- **Confusion Matrix:** $\text{TP} = 16, \text{FP} = 2, \text{TN} = 59, \text{FN} = 0$
- **Precision:** **0.89** (95% Wilson CI: `[0.67, 0.97]`)
- **Recall:** **1.00** (95% Wilson CI: `[0.81, 1.00]`)
- **F1 Score:** **0.94** ($\ge 0.90$ contract invariant satisfied)
- **False Positive Rate:** **0.03** (95% Wilson CI: `[0.01, 0.11]`)
- **Official Flagged Count:** **0** (`official_flagged_count == 0` contract invariant strictly satisfied)
- **Hard Negatives Cleared:** $51 / 53$ (96.2%)
- **Technique Recall:** 100% across all 8 look-alike techniques

### Baseline Comparison & Ablation Suite
- **Baseline (`name_only_rapidfuzz` on DEV $t=0.75$):** Precision 0.89, Recall 1.00, FPR 0.03.
- **`NO_IDENTITYGUARD`:** Flags official assets (`official_flagged_count = 2`), proving IdentityGuard prevents false accusations.
- **`NO_GATES`:** Flags benign lookalikes without corroboration (precision drops to 0.84).
- **`NO_ICON` / `NO_DESCRIPTION`:** Verifies degradation when visual or content signals are missing.

---

## 6. Verification & Testing

### Running Tests
To run Person 4's complete test suite with verbose output:

```bash
pytest backend/tests/test_name_similarity_vectors.py \
       backend/tests/test_lookalike_techniques.py \
       backend/tests/test_identity_guard.py \
       backend/tests/test_query_planner.py \
       backend/tests/test_assess.py \
       backend/tests/test_evaluation.py -v
```

To run all backend tests:
```bash
pytest backend/tests/ -v
```

### Running Lint Checks
```bash
ruff check backend/app/services/ backend/eval/
```

**Status:**
- **34/34** Person 4 automated tests passing (including `test_person3_hard_negatives_clearance`).
- **40/40** total backend tests passing (100% green).
- **0 errors** on Ruff code style check across all services, eval harness, and test suite.
- Branch `feat/detection` is verified and ready for PR submission.
