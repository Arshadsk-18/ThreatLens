# ThreatLens v3 — Digital Risk Protection Platform

[![Contract Version](https://img.shields.io/badge/Contract-v3.0.0%20Frozen-blue.svg)](docs/ARCHITECTURE_API_CONTRACT.md)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.12-green.svg)](pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128.0-009688.svg)](backend/requirements.txt)
[![Linter](https://img.shields.io/badge/Ruff-Passing-brightgreen.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/Tests-83%20Passed%20%7C%209%20XFailed-success.svg)](backend/tests/)

**ThreatLens v3** is an enterprise-grade Digital Risk Protection (DRP) and Brand Defense platform designed to identify impersonation, unauthorized brand usage, and malicious assets across public social networks and mobile application stores (Apple App Store, Bluesky).

Built using a strict **Contract-First Architecture** governed by the frozen single source of truth [docs/ARCHITECTURE_API_CONTRACT.md](docs/ARCHITECTURE_API_CONTRACT.md), ThreatLens enforces rigorous mathematical funnel accounting, airtight separation between offline simulated demo data and live API scans, deterministic brand identity protection (IdentityGuard), and audit-trailed triage decisions.

---

## Table of Contents

1. [Architectural Overview & Core Guarantees](#1-architectural-overview--core-guarantees)
2. [5-Person Team Ownership Matrix](#2-5-person-team-ownership-matrix)
3. [Repository Directory Structure](#3-repository-directory-structure)
4. [API Specifications & Route Directory](#4-api-specifications--route-directory)
5. [Local Development & Setup Guide](#5-local-development--setup-guide)
6. [Testing, Linting & Contract Verification](#6-testing-linting--contract-verification)
7. [Production Deployment Architecture](#7-production-deployment-architecture)
8. [Integration History & Audit Sign-Off](#8-integration-history--audit-sign-off)

---

## 1. Architectural Overview & Core Guarantees

ThreatLens v3 is architected around six non-negotiable invariants:

### 1.1 Contract-First OpenAPI Generation & Parity
The FastAPI backend generates an OpenAPI 3.1 schema that is deeply validated against [docs/openapi.snapshot.json](docs/openapi.snapshot.json) on every test run.
- **Paths:** 19 endpoints across brand management, asset registration, prefill, scanning, finding review, and system status.
- **Operations:** 25 HTTP operations.
- **Zero Hidden Endpoints:** All routes publish `include_in_schema=True`. Zero drift is permitted.

### 1.2 Strict DEMO Network Isolation
- In **`DEMO`** mode, scans load exclusively from local fixture bundles ([backend/app/core/demo_fixtures.py](backend/app/core/demo_fixtures.py)).
- Live network adapters and outgoing sockets/HTTP connections are structurally uncalled.
- If a fixture is missing or malformed, the orchestrator raises `FixtureUnavailableError` and records `PROVIDER_UNAVAILABLE` without ever falling back to a live provider.

### 1.3 LIVE Mode Purity
- In **`LIVE`** mode, clients cannot query fixture sources (`demo_fixtures`, `recorded_fixtures`). Doing so triggers `422 Unprocessable Entity` with error code `MODE_NOT_ALLOWED`.
- A LIVE scan aborts immediately with `ModeNotAllowedException` if any candidate with `source_mode=SourceMode.SIMULATED` is introduced into the pipeline.

### 1.4 Result-Funnel Invariant
Every scan strictly enforces pipeline conservation math:
$$\text{queries\_planned} \le \text{queries\_executed}$$
$$\text{raw\_candidates} \ge \text{analyzed\_candidates}$$
$$\text{analyzed\_candidates} = \text{official\_cleared} + \text{not\_relevant} + \text{benign\_lookalike} + \text{below\_threshold} + \text{findings}$$

### 1.5 Unified Contract Error Envelope
Every non-2xx response is returned in a standardized envelope with an associated `X-Request-ID` HTTP header for distributed tracing:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Brand with ID 12345678-0000-0000-0000-000000000000 not found.",
    "details": {}
  }
}
```

### 1.6 Single-Worker Concurrency & Restart Safety
- **Worker Policy:** Configured for exactly `--workers 1` because background scan jobs and token-bucket provider rate limiters are in-process `asyncio` tasks.
- **Scan Concurrency Guard:** A brand may have only one active scan (`RUNNING` or `QUEUED`) at any given time. Concurrent scan requests return `409 Conflict` (`ACTIVE_SCAN_EXISTS`).
- **Startup Recovery:** Upon application startup, any scans left in `RUNNING` state due to process termination are safely marked as `FAILED` (`SCAN_INTERRUPTED_BY_RESTART`).

---

## 2. 5-Person Team Ownership Matrix

The project development follows a decoupled ownership boundary:

| Role | Domain | Primary Ownership Scope | Dependencies |
| :--- | :--- | :--- | :--- |
| **Person 1** | Frontend & UI | `frontend/**` (React, Vite, Tailwind), OpenAPI client generator | Consumes Person 2 OpenAPI schema |
| **Person 2** | Backend API & Orchestration | `backend/app/main.py`, `app/api/**`, `app/core/**`, `app/schemas/**`, `app/services/orchestration.py`, `render.yaml`, `vercel.json`, `docs/DEPLOY.md` | Provides routes and protocols to teammates |
| **Person 3** | Discovery & Connectors | `backend/app/services/sources/**`, `backend/app/services/image_fetch.py`, `docs/SPIKE_RESULTS.md`, `feat/discovery` | Implements `SourceAdapter` and `fetch_icon_hash` |
| **Person 4** | Detection & Scoring | `backend/app/services/query_planner.py`, `backend/app/services/assess.py`, evaluation harness (`backend/eval/**`) | Pure deterministic `assess()` algorithm |
| **Person 5** | Database & Persistence | `backend/app/repositories/**`, database migrations, SQLite & Supabase persistence, seed scripts | Implements storage behind Person 2 Protocols |

---

## 3. Repository Directory Structure

```text
ThreatLens/
├── .env.example                     # Environment configuration template
├── .gitignore                       # Git exclusion rules
├── pyproject.toml                   # Ruff and Pytest project configuration
├── render.yaml                      # Render Infrastructure-as-Code Blueprint
├── vercel.json                      # Vercel SPA rewrite deployment configuration
├── ThreatLens_v3_Architecture_API_Contract2.md # Initial contract specification
├── docs/
│   ├── ARCHITECTURE_API_CONTRACT.md # Frozen Contract v3.0.0 (Single Source of Truth)
│   ├── DEPLOY.md                    # Production Deployment Guide (Render + Supabase + Vercel)
│   └── openapi.snapshot.json        # Contract-verified OpenAPI schema snapshot
└── backend/
    ├── requirements.txt             # Pinned Python dependencies
    ├── app/
    │   ├── main.py                  # FastAPI application entrypoint & lifespan hooks
    │   ├── api/
    │   │   ├── router.py            # Central router mounting /api/v1 endpoints
    │   │   └── routes/
    │   │       ├── assets.py        # Asset registration, prefill & patch routes
    │   │       ├── brands.py        # Brand CRUD, summary, cleared list & audit trail
    │   │       ├── findings.py      # Findings listing, detail, decision, comparison & evidence
    │   │       ├── health.py        # /health, /ready, /meta system endpoints
    │   │       ├── scans.py         # Brand scan initiation and progress tracking
    │   │       └── sources.py       # Source status catalog and health checks
    │   ├── core/
    │   │   ├── config.py            # Pydantic BaseSettings management
    │   │   ├── demo_fixtures.py     # Offline bundled fixture candidate generator
    │   │   ├── errors.py            # Contract exception hierarchy & HTTP status mappings
    │   │   ├── memory_store.py      # In-memory storage engine & funnel accumulator
    │   │   ├── middleware.py        # Request ID propagation & error envelope handlers
    │   │   ├── prefill_parser.py    # Safe URL parser for store & profile links
    │   │   ├── prefill_service.py   # Prefill lookup orchestrator & adapter registry
    │   │   └── scoring_config.py    # Scoring weight definitions and thresholds
    │   ├── repositories/
    │   │   └── base.py              # Storage repository Protocol definitions (Person 5 boundary)
    │   ├── schemas/
    │   │   ├── asset.py             # Official asset and prefill schemas
    │   │   ├── brand.py             # Brand entity and summary schemas
    │   │   ├── candidate.py         # NormalizedCandidate, QueryPlan, SourceResult
    │   │   ├── common.py            # Pagination and audit schemas
    │   │   ├── comparison.py        # Side-by-side asset comparison breakdown
    │   │   ├── context.py           # Brand and asset context wrappers
    │   │   ├── enums.py             # Contract-defined enums (SourceId, ScanMode, Verdict, etc.)
    │   │   ├── error.py             # Standard API error envelope models
    │   │   ├── finding.py           # Finding item, detail, decision patch models
    │   │   ├── health.py            # System health and readiness responses
    │   │   ├── meta.py              # System metadata schema
    │   │   ├── scan.py              # Scan request, status, options, funnel models
    │   │   ├── scoring.py           # Assessment breakdown and signal result models
    │   │   └── source.py            # Source health check schema
    │   └── services/
    │       ├── assess.py            # Scoring Protocol & stub (Person 4 boundary)
    │       ├── image_fetch.py       # Safe icon fetch & pHash Protocol (Person 3 boundary)
    │       ├── orchestration.py     # Central scan pipeline & adapter dispatcher
    │       ├── query_planner.py     # Query planner Protocol (Person 4 boundary)
    │       └── sources/
    │           └── base.py          # SourceAdapter Protocol (Person 3 boundary)
    └── tests/
        ├── conftest.py              # Pytest fixtures & FastAPI TestClient
        ├── test_api_brands_assets.py# Brand & asset CRUD, prefill SSRF validation
        ├── test_api_findings_sources.py # Source status, triage decisions, comparison
        ├── test_api_scans.py        # Scan lifecycle, concurrency 409, funnel math, isolation
        ├── test_deploy_smoke.py     # Deployment readiness, CORS preflight, crash recovery
        ├── test_error_envelope.py   # Standard error envelopes & X-Request-ID propagation
        ├── test_health_meta.py      # Health, ready, and meta endpoints
        ├── test_openapi_matches_contract.py # Snapshot equality & schema integrity
        ├── test_schemas_import.py   # Schema instantiation and Protocol sanity
        └── test_section_18_3_must_pass.py # Formal Contract Section 18.3 conformance suite
```

---

## 4. API Specifications & Route Directory

All endpoints are mounted under `/api/v1`. The interactive Swagger documentation is available at `/docs` and Redoc at `/redoc`.

### 4.1 System & Monitoring (`/api/v1`)
| Method | Path | Summary | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness check | Returns `{"status": "ok"}` for container orchestrators. |
| `GET` | `/ready` | Readiness check | Validates database connectivity without leaking credentials. |
| `GET` | `/meta` | System metadata | Returns service version, git commit, and environment info. |

### 4.2 Brand & Official Asset Management (`/api/v1/brands`)
| Method | Path | Summary | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/brands` | List brands | Paginated list of registered monitored brands. |
| `POST` | `/brands` | Register brand | Create brand profile with industry category and aliases. |
| `GET` | `/brands/{id}` | Get brand | Retrieve brand details by UUID. |
| `GET` | `/brands/{id}/summary` | Brand summary | High-level threat aggregates (active findings, scans, risk index). |
| `GET` | `/brands/{id}/cleared` | Cleared list | Assets cleared as official, namesake, or below threshold. |
| `GET` | `/brands/{id}/audit` | Brand audit trail | Immutable chronological log of decisions and asset updates. |
| `GET` | `/brands/{id}/assets` | List assets | Monitored official assets registered for a brand. |
| `POST` | `/brands/{id}/assets` | Register asset | Add verified official app or social account with stable ID. |
| `POST` | `/brands/{id}/assets/prefill` | Prefill draft | Safe URL lookup (App Store / Bluesky) to auto-populate asset details. Blocks SSRF and private IP ranges. |
| `PATCH` | `/brands/{id}/assets/{asset_id}` | Update asset | Toggle active status, publisher trust, or update metadata. |

### 4.3 Scan Pipeline & Orchestration (`/api/v1/brands/{id}/scans`)
| Method | Path | Summary | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/brands/{id}/scans` | Start scan | Launch scan in `DEMO` or `LIVE` mode. Blocks concurrent scans with `409 Conflict`. |
| `GET` | `/brands/{id}/scans` | List brand scans | Paginated scan history for a brand. |
| `GET` | `/scans/{scan_id}` | Get scan status | Real-time progress percentage, stage, funnel counts, and source outcomes. |

### 4.4 Sources Status (`/api/v1/sources`)
| Method | Path | Summary | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/sources/status` | Source coverage | Returns catalog of 9 contract sources. Supports `refresh=true` for active health checks. |

### 4.5 Findings & Review Triage (`/api/v1/findings`)
| Method | Path | Summary | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/findings` | List findings | Search and filter findings by brand, severity, status, source. |
| `GET` | `/findings/{id}` | Get finding detail | Deep dive into candidate details, signals, and matched assets. |
| `PATCH` | `/findings/{id}/decision` | Analyst triage | Transition status (`CONFIRMED`, `DISMISSED`, `TAKEDOWN_REQUESTED`) with mandatory justification. |
| `GET` | `/findings/{id}/comparison` | Asset comparison | Side-by-side diff against official brand asset (name diff, icon hash). |
| `GET` | `/findings/{id}/evidence` | Evidence bundle | Raw JSON evidence payload for takedown reporting. |

---

## 5. Local Development & Setup Guide

### 5.1 Prerequisites
- **Python:** 3.10 or 3.12 (Python 3.12 recommended for production parity)
- **Package Manager:** `pip`

### 5.2 Environment Setup
1. Clone the repository and navigate to the project root:
   ```bash
   git clone https://github.com/Arshadsk-18/ThreatLens.git
   cd ThreatLens
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Configure environment variables:
   ```bash
   cp .env.example backend/.env
   ```

### 5.3 Running the Development Server
Launch the FastAPI development server from the repository root:
```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
Once started:
- API Base: `http://127.0.0.1:8000/api/v1`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health Endpoint: `http://127.0.0.1:8000/api/v1/health`

---

## 6. Testing, Linting & Contract Verification

### 6.1 Running the Linter
The codebase strictly adheres to Ruff formatting and lint rules:
```bash
python -m ruff check .
```

### 6.2 Running the Test Suite
ThreatLens features comprehensive unit, integration, and contract tests:
```bash
# Run all tests
python -m pytest -v

# Run OpenAPI snapshot & contract parity tests
python -m pytest -v backend/tests/test_openapi_matches_contract.py

# Run DEMO & LIVE network isolation tests
python -m pytest -v backend/tests/test_api_scans.py -k "demo or live"

# Run deployment smoke tests
python -m pytest -v backend/tests/test_deploy_smoke.py
```

### 6.3 Test Status Summary
- **Total Tests:** 92
- **Passing Tests:** 83 (100% of Person 2 backend & API routing scope)
- **XFailed Tests:** 9 (Explicitly bounded to pending teammate features):
  - 1 on **Person 3**: `test_image_fetch_blocks_non_allowlisted_hosts` (waiting for safe pHash downloader).
  - 8 on **Person 4**: Pure `assess()` scoring algorithms, G5 safeguard rules, vector similarity, and Wilson confidence interval.

---

## 7. Production Deployment Architecture

The production setup uses a multi-cloud serverless and containerized topology:

```mermaid
graph TD
    User([End User / Analyst]) --> Vercel[Vercel SPA Frontend]
    Vercel -->|CORS Restrictive /api/v1| Render[Render Web Service - FastAPI]
    Render -->|Pooled SSL Port 6543| Supabase[(Supabase PostgreSQL)]
    Render -.->|Offline DEMO Mode| Fixtures[Local JSON Fixtures]
    Render -.->|LIVE Mode Only| Providers[External Providers: Apple iTunes / Bluesky]
```

### 7.1 Component Breakdown
1. **Backend (Render Web Service):**
   - Configured via [render.yaml](render.yaml).
   - Starts with `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`.
   - Health check registered at `/api/v1/health`.
2. **Database (Supabase PostgreSQL):**
   - Utilizes Supavisor transaction pooler on port `6543` with mandatory SSL (`?sslmode=require`).
3. **Frontend (Vercel):**
   - Single-page application configured via [vercel.json](vercel.json).
   - Communicates with backend using environment variable `VITE_API_URL`.

For detailed, step-by-step deployment instructions, refer to the [docs/DEPLOY.md](docs/DEPLOY.md) guide.

---

## 8. Integration History & Audit Sign-Off

### 8.1 Critical Blocker Remediations on Branch `feat/api`
During the formal integration verification against Contract v3.0.0, two primary blockers were identified and successfully remediated:

1. **OpenAPI Schema Suppression (Finding 1):**
   - *Issue:* Routes (`/sources/status`, `/findings`, `/brands/{id}/cleared`, `/brands/{id}/audit`) had been hidden via `include_in_schema=False`, and the `field="icon"` comparison item was omitted.
   - *Resolution:* All routes were unmasked with `include_in_schema=True`, comparison schemas were fully reconciled with Section 11.5, and the OpenAPI schema snapshot was regenerated to achieve 100% equality with 0 discrepancies.
2. **DEMO Scan Network Isolation (Finding 2):**
   - *Issue:* In `DEMO` scans, the orchestrator evaluated live adapter lookups and risked calling live external services on missing fixtures.
   - *Resolution:* Structurally restructured `_fetch_source` in [orchestration.py](backend/app/services/orchestration.py) to branch into local fixtures first. Added tests proving 0 socket connections, 0 HTTP requests, and that registered live adapters are never called.

### 8.2 Final Verification Verdict
- **Finding 1 (OpenAPI & Contract Parity):** `PASS`
- **Finding 2 (DEMO Strict Network Isolation):** `PASS`
- **Person 2 Ownership Compliance:** Verified within lane.
- **Merge Gate Recommendation:** **`APPROVE FOR MERGE`** (Ready for teammate integration with Person 3, 4, and 5).

---

## License & Contributing
This repository is developed as part of the ThreatLens v3 engineering sprint. All changes are strictly governed by [docs/ARCHITECTURE_API_CONTRACT.md](docs/ARCHITECTURE_API_CONTRACT.md). Any proposed changes to API paths, schemas, or enums require a formal contract amendment.
