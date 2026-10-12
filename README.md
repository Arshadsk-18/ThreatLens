# ThreatLens v3 — Digital Risk Protection Engine

> **HacXLerate 2026** · Challenge 3: Digital Risk Protection — Social & App Monitoring (Kampus.VC)  
> **Architecture Contract:** `3.0.0` · **API Prefix:** `/api/v1`  
> **Team Role:** Person 5 (Database, QA, Seed & Reporting) · **Branch:** `feat/database-qa`

ThreatLens surfaces **candidates for review**, never unverified criminals. Official assets are excluded by **exact identity evidence**, never by name similarity. Every result exposes its underlying evidence, source mode, and observation timestamp. LIVE, CACHED, SIMULATED, NOT_CONNECTED, and ERROR states are never silently conflated.

---

## 1. Executive Summary & Core Philosophy

ThreatLens protects brands against look-alike applications, impersonating social media profiles, and credential phishing lures across public app catalogs and decentralized social networks.

### Non-Negotiable Architectural Principles
1. **Candidates for Review:** Copy never claims "scam", "fake", or "malicious" about an unconfirmed candidate. Only an authorized human analyst can transition a candidate to `CONFIRMED_SUSPICIOUS`.
2. **Identity by ID, Not Name:** Name similarity finds suspects—it never clears anyone. Legitimate assets are cleared strictly by cryptographic DIDs, bundle IDs, and registered developer IDs.
3. **No Silent Fallbacks:** An unavailable or rate-limited provider displays an explicit status (`NOT_CONNECTED` / `RATE_LIMITED` / `ERROR`), never an artificial 0-threats "clean" result.
4. **Strict Mode Isolation:** `LIVE` scans never contain simulated records. `DEMO` scans make zero outbound network calls.
5. **Evidence-First Dossiers:** Every point of risk traces to observable facts with sources and UTC timestamps.
6. **Deterministic Scoring:** Identity decisions and risk scores are calculated via deterministic gates and weighted signal groups—never delegated to probabilistic LLMs.
7. **Decision Memory:** When an analyst dismisses a false positive, that decision persists across subsequent rescans unless the candidate's observable content changes (`content_hash` mismatch).

---

## 2. Team Division of Labor & Person 5 Ownership

ThreatLens is engineered by a 5-person team operating under strict interface contracts:

| Person | Focus Area | Branch | Scope & Allowed Files |
|---|---|---|---|
| **Person 1** | Frontend UI & Design System | `feat/frontend` | `frontend/**` |
| **Person 2** | API Routes & Integration Lead | `feat/api` | `backend/app/main.py`, `core/**`, `api/routes/**`, `schemas/**` |
| **Person 3** | Discovery & Connectors | `feat/discovery` | `services/sources/**`, `services/image_fetch.py`, spike fixtures |
| **Person 4** | Detection, Scoring & Eval | `feat/detection` | `services/{assess,identity_guard,scoring,compare}/**`, `backend/eval/**` |
| **Person 5** *(Our Role)* | **Database, QA & Reporting** | `feat/database-qa` | **`backend/app/db/**`, `backend/app/repositories/**`, `backend/tests/**`, `docs/DEPLOY.md`, `docs/DEMO_CHECKLIST.md`** |

### Person 5 Definition of Done (DoD) — All Completed
- [x] **Relational Schema**: 10 portable SQLAlchemy 2.0 tables implemented without vendor-specific extensions.
- [x] **Dual Persistence Engine**: Verified with parity across SQLite (local/in-memory) and Supabase PostgreSQL over SSL.
- [x] **Repository Layer**: 8 Repository Protocols implemented in-memory and via SQLAlchemy 2.0 behind identical interfaces.
- [x] **Demo Story & Seed Engine**: 60-fixture Kaveri Bank demo manifest (Appendix B) with strictly idempotent seeding.
- [x] **Reporting & Export**: Forensic evidence dossiers and spreadsheet-formula-safe CSV export (`findings_to_csv`).
- [x] **DEMO Safety Harness**: Air-gapped socket blocking, live isolation, and failure resilience.
- [x] **Live Database Proofs**: 3 end-to-end rehearsals executed on deployed Supabase PostgreSQL logging real timings.
- [x] **Documentation**: Deployed seed guide ([`run_seed.md`](file:///c:/Users/SUKUMAR/ThreatLens/backend/app/db/seed/run_seed.md)), deployment guide ([`DEPLOY.md`](file:///c:/Users/SUKUMAR/ThreatLens/docs/DEPLOY.md)), and full demo checklist ([`DEMO_CHECKLIST.md`](file:///c:/Users/SUKUMAR/ThreatLens/docs/DEMO_CHECKLIST.md)).

---

## 3. Database Architecture (Section 9)

Located in [`backend/app/db/`](file:///c:/Users/SUKUMAR/ThreatLens/backend/app/db/):

```
backend/app/db/
├── base.py              # Base declarative model, UUID generator, UTC helpers
├── models.py            # 10 SQLAlchemy 2.0 portable domain models
├── session.py           # Engine factory, SSL configuration, init_db(), scan recovery
├── POSTGRES_NOTES.md    # Real findings from Supabase PostgreSQL verification
└── seed/
    ├── fixtures_manifest.json  # 60 Kaveri Bank demo fixtures (Appendix B)
    ├── generate_manifest.py    # Deterministic fixture generator
    ├── seed.py                 # Idempotent seed engine
    ├── run_seed.md             # Deployed database seed execution guide
    └── README.md               # Seed architecture and invariant documentation
```

### 3.1 The 10 Core Relational Tables
1. **`brands`**: Registered entities with official domains, distinctive tokens, and industry categorization.
2. **`official_assets`**: Legitimate apps and profiles. Compound unique constraint on `(brand_id, platform, stable_identifier)`.
3. **`scans`**: In-process scan lifecycle tracking (`queued` → `planning` → `fetching` → `clearing` → `assessing` → `completed`), progress percent, and event log capped at 200 events.
4. **`candidate_assets`**: Ingested third-party assets keyed on `(brand_id, platform, stable_identifier)`, content hashing for change detection, and analyst review status (`NEW`, `CONFIRMED_SUSPICIOUS`, `DISMISSED_FALSE_POSITIVE`).
5. **`assessments`**: Deterministic scoring outcomes, risk score (0–100), severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`), IdentityGuard rule, corroborating signal groups, gates applied, and evidence coverage.
6. **`evidence`**: Observable forensic facts (field name, observed value, source URL, observed timestamp).
7. **`analyst_decisions`**: Immutable records of analyst review actions with mandatory reason strings.
8. **`audit_events`**: Immutable compliance audit trail capturing system and analyst actions.
9. **`response_cache`**: HTTP response cache with key hashing and TTL expiration.
10. **`evaluation_runs`**: Offline evaluation benchmark records (`precision`, `recall`, `f1`, `wilson_intervals`).

### 3.2 Portability & Engine Configuration
- **Portable Types**: Standard 36-character UUID strings, SQLAlchemy generic `JSON`, and timezone-aware UTC timestamps (`DateTime(timezone=True)`). No SQLite-only or PostgreSQL-only dialect types.
- **Connection Normalization**: Automatically normalizes legacy `postgres://` URLs to `postgresql://` (or `postgresql+psycopg2://`).
- **SSL Enforcement**: Mandatory `sslmode=require` configured automatically for all remote PostgreSQL endpoints.
- **PgBouncer Pooling**: Configured with `pool_pre_ping=True` and connection recycling to handle serverless pooler timeouts.
- **Server Restart Recovery**: `mark_interrupted_scans(session)` marks any scan left in `RUNNING` or `QUEUED` as `FAILED` on application startup with the message *"Interrupted by server restart"*.

---

## 4. Repository Layer & Dual Protocol Pattern (Section 12)

Located in [`backend/app/repositories/`](file:///c:/Users/SUKUMAR/ThreatLens/backend/app/repositories/):

```
backend/app/repositories/
├── protocols.py        # Strict Python typing Protocols matching Section 12
├── in_memory.py        # Thread-safe in-memory repository bundle (rapid development)
├── sqlalchemy_repo.py  # Production SQLAlchemy 2.0 implementation
├── export.py           # Evidence dossier and formula-safe CSV export
└── __init__.py         # Package exports
```

### 4.1 Implemented Protocols
- **`BrandRepo`**: `create`, `get`, `get_by_name`, `list`
- **`AssetRepo`**: `create_official`, `get_official`, `list_official_for_brand`
- **`ScanRepo`**: `create`, `get`, `update_progress`, `append_event` (capped at 200), `finish`, `list_for_brand`
- **`CandidateRepo`**: `upsert` (race-safe atomic upsert preserving decision memory), `get`, `get_by_stable_id`, `list_for_brand`
- **`AssessmentRepo`**: `save` (stores score breakdown, gates, corroborating groups, and evidence rows atomically), `get`, `list_findings` (supports `latest_only=True` via window functions and `include_dismissed`), `list_cleared`
- **`DecisionRepo`**: `record` (enforces mandatory reason for `DISMISSED_FALSE_POSITIVE` and `CONFIRMED_SUSPICIOUS`, logs audit event atomically), `list_by_candidate`
- **`CacheRepo`**: `get` (with `max_age_s` TTL validation), `put`, `purge_expired`
- **`AuditRepo`**: `record`, `list`

### 4.2 Technical Highlights
- **Single-Query Latest Findings**: Implemented in `SqlAlchemyAssessmentRepo.list_findings` using SQL window functions (`func.row_number().over(partition_by=Assessment.candidate_asset_id, order_by=desc(Assessment.created_at))`), avoiding N+1 Python loops.
- **Decision Memory Suppression & Resurfacing**: If an analyst dismisses candidate $C_1$, subsequent scans keep $C_1$ hidden from the active review queue. If the candidate updates their profile (changing the SHA-256 `content_hash`), $C_1$ immediately resurfaces with `changed_since_decision=True`.
- **Formula Injection Defense (`export.py`)**: `findings_to_csv` sanitizes spreadsheet injection vectors by prefixing any cell beginning with `=`, `+`, `-`, `@`, `\t`, or `\r` with a single quote (`'`), while respecting RFC 4180 quoting.

---

## 5. Kaveri Bank Demo Story & Idempotent Seed (Appendix B)

To guarantee a reliable, reproducible evaluation and presentation flow, Person 5 codified the official demo story for **Kaveri Bank** (a fictional commercial bank):

### 5.1 Composition (60 Candidates Ingested)
- **5 Cleared by Identity (IdentityGuard Proof)**:
  1. Official iOS App (`1234567890`, bundle ID `com.kaveribank.mobile`) — Rule **R1_EXACT_ID**
  2. Official Bluesky Profile (`did:plc:kaveriofficial123`) — Rule **R1_EXACT_ID**
  3. Utility App by same developer (`9000000001`) — Rule **R2_PUBLISHER_ID**
  4. Authorized Partner App (`com.kaveripartner.loans`) — Rule **R3_PARTNER**
  5. Official Android App (`com.kaveribank.android`, simulated) — Rule **R1_EXACT_ID**
- **14 Benign Lookalikes (Over-Flagging Defense)**:
  - 13 Unrelated commercial namesakes (Kaveri Silks, Kaveri Logistics, Kaveri Travels) — Cleared under Gate **G4_UNRELATED_CATEGORY**
  - 1 Fan page with explicit disclaimer and clean profile — Cleared under Gate **G5_DECLARED_UNOFFICIAL**
- **12 Impersonation Candidates (Lookalike Technique Matrix)**:
  - Covers all 9 lookalike techniques: `HOMOGLYPH` (Cyrillic `\u0456`), `CHARACTER_SWAP`, `OMISSION`, `ADDED_WORD`, `SPACING`, `SEPARATOR`, `EXACT_NAME_REUSE` (capped at `MEDIUM`), `REPETITION`, `KEYBOARD_ADJACENT`.
- **29 Not Relevant Results**:
  - Distant string matches filtered out by early relevance gate G1.

### 5.2 Mathematical Funnel Invariant
The scan funnel rigorously accounts for all ingested candidates without dropouts:
$$\text{Deduplicated (60)} = \text{Official Cleared (5)} + \text{Not Relevant (29)} + \text{Benign Lookalikes (14)} + \text{Below Threshold (0)} + \text{Findings (12)}$$

---

## 6. Live Database Verification & Rehearsals

### 6.1 Supabase PostgreSQL DoD Verification
Verified on a live Supabase PostgreSQL 17 instance in AWS `ap-south-1` via pooled connection strings over SSL:
- `create_all` initializes all 10 tables cleanly on first start.
- JSON serialization/deserialization verified for complex breakdown arrays.
- UUID strings remain stable across reloads without truncation.
- Timezones remain timezone-aware UTC.
- Unique constraints raise `IntegrityError` predictably.
- Findings query produces identical results on PostgreSQL and SQLite.

### 6.2 Three Deployed End-to-End Rehearsals (Section 20 Risk Register)
Executed three complete rehearsals against live Supabase PostgreSQL measuring wall-clock latency:
```text
ALL 3 REHEARSALS COMPLETED SUCCESSFULLY:
  Rehearsal 1: 72.55s
  Rehearsal 2: 71.32s
  Rehearsal 3: 76.96s
```
- **Cold-Start Warm-Up Observation**: Ping 1 took **1.61s** (initial TLS + PgBouncer connection handshake), while warm Pings 2 & 3 executed in **0.26s** and **0.29s** (~6x faster).
- **Decision Memory Discovery**: Rehearsal 1 exercised an analyst dismissal. Rehearsal 2 confirmed that `list_findings(include_dismissed=False)` returned 11 active findings, while `include_dismissed=True` returned 12, experimentally proving cross-scan decision memory.

---

## 7. Section 18.3 Must-Pass Automated Test Suite

All 22 tests required by Section 18.3 are codified in [`backend/tests/test_must_pass_18_3.py`](file:///c:/Users/SUKUMAR/ThreatLens/backend/tests/test_must_pass_18_3.py):

| # | Test Name | Status | Real Reason | Owner |
|---|---|---|---|---|
| 1 | `test_openapi_matches_contract` | **SKIP** | Person 2 blocker: `backend/app/main.py` routes not yet merged on branch | Person 2 |
| 2 | `test_api_error_http_mapping` | **SKIP** | Person 2 blocker: `backend/app/main.py` HTTP error handlers not yet merged | Person 2 |
| 3 | `test_prefill_rejects_unlisted_urls` | **SKIP** | Person 2 blocker: `app.services.prefill` URL validator not yet merged | Person 2 |
| 4 | `test_image_fetch_blocks_non_allowlisted_hosts` | **SKIP** | Person 2 blocker: `app.services.images` host allowlist not yet merged | Person 2 |
| 5 | `test_scan_funnel_invariant` | **PASS** | 60 deduplicated == 5 cleared + 29 not relevant + 14 benign + 0 below threshold + 12 findings | **Person 5** |
| 6 | `test_official_app_never_flagged` | **PASS** | Official iOS & Android apps cleared under R1_EXACT_ID (risk_score = 0; 0 in findings) | **Person 5** |
| 7 | `test_official_social_never_flagged` | **PASS** | Official Bluesky DID `did:plc:kaveriofficial123` cleared under R1_EXACT_ID | **Person 5** |
| 8 | `test_publisher_id_clears_second_app` | **PASS** | Registered developer ID `9000000001` clears second app under R2_PUBLISHER_ID | **Person 5** |
| 9 | `test_namesake_not_flagged` | **PASS** | 14 benign lookalikes cleared under G4_UNRELATED_CATEGORY & G5_DECLARED_UNOFFICIAL | **Person 5** |
| 10 | `test_name_only_capped_at_medium` | **PASS** | Exact name match without corroborating evidence capped at MEDIUM (score <= 49) | **Person 5** |
| 11 | `test_lookalike_techniques` | **PASS** | All 9 lookalike techniques represented across active findings | **Person 5** |
| 12 | `test_declared_unofficial_cannot_hide_copied_avatar` | **SKIP** | Person 4 blocker: `app.services.assess` scoring pipeline not yet merged | Person 4 |
| 13 | `test_declared_unofficial_requires_clean_lure_and_links` | **SKIP** | Person 4 blocker: `app.services.assess` scoring pipeline not yet merged | Person 4 |
| 14 | `test_g5_never_applies_to_exact_name_or_homoglyph` | **SKIP** | Person 4 blocker: `app.services.assess` scoring pipeline not yet merged | Person 4 |
| 15 | `test_name_similarity_vectors` | **SKIP** | Person 4 blocker: `app.services.scoring.text` module not yet merged | Person 4 |
| 16 | `test_wilson_interval` | **SKIP** | Person 4 blocker: `app.services.eval.metrics` module not yet merged | Person 4 |
| 17 | `test_eval_metrics_computed_not_hardcoded` | **SKIP** | Person 4 blocker: `app.services.eval.evaluator` dataset runner not yet merged | Person 4 |
| 18 | `test_demo_scan_makes_no_network_calls` | **PASS** | `socket.socket.connect` blocked via monkeypatch; zero network calls made | **Person 5** |
| 19 | `test_live_scan_has_no_simulated_records` | **PASS** | LIVE scan rejects `source_mode=SIMULATED`; enforces `source_mode=LIVE` | **Person 5** |
| 20 | `test_not_connected_is_not_an_error` | **PASS** | Disconnected sources recorded as `NOT_CONNECTED` without failing scan status | **Person 5** |
| 21 | `test_provider_failure_is_not_clean_result` | **PASS** | `respx.mock` HTTP 500 error records `FAILED` status, never claiming 0 threats | **Person 5** |
| 22 | `test_decision_memory_persists` | **PASS** | Dismissed candidates stay hidden on rescan; resurface when `content_hash` changes | **Person 5** |

- **Person 5 Integration Suite Result**: **33 PASSED, 2 SKIPPED** in 10.73s.
- **Full Backend Test Suite**: **57 PASSED, 12 SKIPPED, 0 FAILED** in 2m 53s across 69 test items.

---

## 8. Presentation & Operational Documentation

| Document | Purpose | Key Content |
|---|---|---|
| [`docs/DEMO_CHECKLIST.md`](file:///c:/Users/SUKUMAR/ThreatLens/docs/DEMO_CHECKLIST.md) | Presentation runbook & rehearsal logs | T-5 min / T-0 min health check, 5 staged browser tabs, 3-minute click path, Section 15.3 copy guide, Section 18.2 acceptance checklist, 3 live rehearsal logs, and fallback video script. |
| [`backend/app/db/seed/run_seed.md`](file:///c:/Users/SUKUMAR/ThreatLens/backend/app/db/seed/run_seed.md) | Deployed database seeding guide | Exact shell command to run seed on deployed backend, idempotency verification, and curl/jq verification steps. |
| [`docs/DEPLOY.md`](file:///c:/Users/SUKUMAR/ThreatLens/docs/DEPLOY.md) | Deployment configuration for Person 2 | Pooled PgBouncer connection string, SSL requirement, `create_all` in FastAPI lifespan, single-worker rule, and cold-start mitigations. |
| [`backend/app/db/POSTGRES_NOTES.md`](file:///c:/Users/SUKUMAR/ThreatLens/backend/app/db/POSTGRES_NOTES.md) | Real database audit findings | Dialect normalization, port differences (5432 session vs 6543 transaction), WAN latency findings, and event batching recommendations. |

---

## 9. Quickstart & Verification Guide

### 9.1 Environment Setup
```bash
# Clone the repository
git clone https://github.com/Arshadsk-18/ThreatLens.git
cd ThreatLens

# Switch to database QA branch
git checkout feat/database-qa

# Install backend dependencies
cd backend
pip install -r requirements.txt
```

### 9.2 Run the Idempotent Seed
```bash
# Seed Kaveri Bank demo story against local SQLite (creates backend/threatlens.db)
python -m app.db.seed.seed
```

### 9.3 Run the Test Suites
```bash
# Run Person 5's Section 18.3 must-pass tests
pytest tests/test_must_pass_18_3.py -v

# Run models and export test suites
pytest tests/test_persistence_models.py tests/test_persistence_export.py -v

# Run demo safety and network isolation tests
pytest tests/test_e2e_demo.py -k "not test_e2e_demo_scan_flow" -v

# Run repository tests across in-memory and SQLite backends
pytest tests/test_persistence_repositories.py -k "in_memory or sqlalchemy_sqlite" -v

# Verify code formatting and linting
ruff check app tests
ruff format --check app tests
```

---

## 10. Repository Integrity & Commit History

```text
* eafed58 feat(docs, tests): add demo checklist, 3 live rehearsals, fallback script, and complete 18.3 test suite
* be329b0 feat(tests, docs): add E2E demo test harness, section 18.3 tests, run_seed guide, and DEPLOY docs
* cafea24 feat(db, repositories): verify Supabase Postgres persistence DoD and add export helpers
* d59b2ad feat(seed): add Kaveri Bank demo fixtures manifest, idempotent seed, and QA story tests
* 531643f feat(repositories): implement in-memory and SQLAlchemy repositories with shared test suite
* 47f76b7 feat(db): implement Section 9 SQLAlchemy 2.0 models and session management
* 221983b Add files via upload
```

- **Branch Status**: Up to date, working tree clean.
- **Credential Hygiene**: 0 secrets committed.
- **Code Health**: 100% compliant with Python 3.12+, SQLAlchemy 2.0, and Ruff styling standards.
