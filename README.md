# ThreatLens v3 — Discovery & Source Connectors (`feat/discovery`)

**Role:** Person 3 — Discovery and Source Connectors Engineer  
**Branch:** `feat/discovery`  
**Contract Version:** `3.0.0` (`docs/ARCHITECTURE_API_CONTRACT.md`)  
**Test Suite:** 683 automated unit, contract, and property tests passing (0 failures)

---

## Overview

ThreatLens surfaces **candidates for review** across public application stores and social networks without fabricating live data or confusing simulated datasets with real signals.

This branch (`feat/discovery`) implements the complete discovery and source connector layer under `backend/app/services/sources/` and safe asset acquisition in `backend/app/services/image_fetch.py`. All components conform strictly to **Contract Version 3.0.0** internal Python interfaces (Section 12), rate-limiting and security rules (Sections 5.5 and 5.6), and source specifications (Section 13).

---

## Architecture & Components

```
                          ThreatLens Scan Pipeline
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
┌──────────────────────┐                           ┌──────────────────────┐
│  Live Connectors     │                           │  Offline Adapters    │
│  ──────────────────  │                           │  ──────────────────  │
│  • apple_itunes      │                           │  • demo_fixtures     │
│  • bluesky_public    │                           │  • recorded_fixtures │
└──────────┬───────────┘                           └──────────┬───────────┘
           │                                                   │
           ├───────────────── Rate Limiting (Leaky Bucket) ────┤
           ├───────────────── Response Cache & Stale Fallback ─┤
           ▼                                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Central Source Registry                           │
│     All 9 Contract-Defined Source IDs (LIVE / SIMULATED / NOT_CONN)     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────┐
                    │  NormalizedCandidate Converter  │
                    │   (Contract Section 12 Schema)  │
                    └────────────────┬────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────┐
                    │      Safe Image Fetcher         │
                    │   (pHash Perceptual Hashing)    │
                    └─────────────────────────────────┘
```

---

## Delivered Modules

### 1. Central Source Registry (`services/sources/registry.py`)
Maintains the exact catalog of nine fixed source IDs defined in Contract Section 11.1:
1. `apple_itunes` — Live catalog discovery via Apple iTunes Search API (`LIVE`, `CACHED`).
2. `bluesky_public` — Live actor discovery and batch profile enrichment (`LIVE`, `CACHED`).
3. `bluesky_posts` — Post search disabled for unauthenticated P0 (`NOT_CONNECTED`).
4. `google_play_snapshot` — Unofficial scraping prohibited (`NOT_CONNECTED`).
5. `instagram` — Platform API access required (`NOT_CONNECTED`).
6. `x` — Platform API access required (`NOT_CONNECTED`).
7. `facebook` — Platform API access required (`NOT_CONNECTED`).
8. `demo_fixtures` — Pure local JSON loader for DEMO scans (`SIMULATED`).
9. `recorded_fixtures` — Replay of real captured spike responses (`CACHED`).

- **Mode Isolation:** Enforces `assert_not_demo_only()` and `get_adapter(..., is_live_scan=True)` to guarantee LIVE scans never receive simulated or demo adapters.
- **Dynamic Catalog:** `source_catalog()` reports real-time health and previous execution status across all 9 adapters.

### 2. Apple iTunes Adapter (`services/sources/apple.py`)
- **API Endpoints:**
  - Search: `https://itunes.apple.com/search?term=<query>&entity=software&country=in&limit=<n>`
  - Lookup: `https://itunes.apple.com/lookup?id=<trackId>` or `?bundleId=<bundleId>`
- **Specifications & Guardrails:**
  - Token-bucket limiter: $\le 1$ request per 3.0 s.
  - HTTP timeout: 8.0 s total.
  - Retry policy: 1 retry on 5xx or connection timeout; strictly **0 retries on 429**.
  - Query sanitization: Truncates queries to $\le 100$ characters.
  - Result cap: Hard maximum of 50 candidates per execution.
  - Localization: Configurable store country via `APPLE_COUNTRY` (default: `"in"`).

### 3. Bluesky Public Adapter (`services/sources/bluesky.py`)
- **API Endpoints:**
  - Discovery: `https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors`
  - Enrichment: `https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles` (batched up to 25 DIDs)
- **Specifications & Guardrails:**
  - Limiter: $\le 1$ request per second.
  - Self-label compliance: Automatically skips accounts with `no-unauthenticated` or `!no-unauthenticated` self-labels.
  - Link extraction: Regex parses URLs from multiline bio text and `website` field into `external_links`.
  - P0 Boundary: Anonymous `searchPosts` returns 403 on the public AppView and is marked `NOT_CONNECTED`.

### 4. Safe Image Fetch & Perceptual Hashing (`services/image_fetch.py`)
- **Signature:** `async def fetch_icon_hash(url: str) -> str | None`
- **Security Protections (Section 5.6):**
  - **HTTPS Only:** Rejects plaintext HTTP, userinfo credentials, and non-443 explicit ports.
  - **Host Allowlist:** Only downloads from `*.mzstatic.com` and `cdn.bsky.app`. Rejects IP literals and spoofed subdomains.
  - **Strict Redirects:** Manual redirect handler (max 3 hops); cross-host redirects immediately return `None`.
  - **Resource Caps:** 2 MB maximum body size (checked via `Content-Length` and enforced during streaming); 5 s total timeout.
  - **Image Validation:** Verifies `Content-Type: image/*` and enforces Pillow decompression bomb limits (`MAX_IMAGE_PIXELS = 10_000_000`).
  - **Perceptual Hashing:** Generates standard 64-bit perceptual hash hex string (`imagehash.phash`). Returns `None` on any failure without raising exceptions.

### 5. URL Prefill Parser (`services/sources/prefill.py`)
- **Purpose:** Enables store-link prefill for brand registration without fetching arbitrary user-supplied URLs.
- **Allowlisted Patterns:**
  - Apple App Store: `https://apps.apple.com/<cc>/app/<slug>/id<digits>`
  - Bluesky: `https://bsky.app/profile/<handle-or-did>`
  - Direct identifiers: `("apple_app_store", "<digits-or-bundle>")`, `("bluesky", "<handle-or-did>")`
- **SSRF Protection:** Rejects newline injections, Unicode Cyrillic homoglyphs, backslashes, userinfo tricks, and private network IPs.

### 6. Transparent Caching Layer (`services/sources/cache.py`)
- **Interface:** Adheres to the `CacheRepo` protocol (`get` / `put`). Includes `InMemoryCacheFake` for standalone testing.
- **Deterministic Keys:** Canonical SHA-256 hash over `{source_id, operation, sanitized_params}`.
- **Cache Invariants:**
  - TTL configured via `CACHE_TTL_SECONDS` (default: 3600 s).
  - Bypassed when `force_refresh=True`.
  - `allow_stale_cache=True` serves expired entries labelled `PARTIAL` while preserving original `retrieved_at`.
  - Failed provider responses are **never cached**.

### 7. Fixture Adapters & Handoff Support (`services/sources/fixtures_*.py`)
- **Demo Fixtures (`DemoFixtureAdapter`):**
  - Reads `backend/tests/fixtures/demo/*.json`.
  - Enforces `fixture_version == 1` and `records: list` envelope.
  - Validates `source_mode == SIMULATED`; rejects `LIVE` or `CACHED` records with filename and record index.
  - Zero network calls: socket connections raise `RuntimeError`.
- **Recorded Fixtures (`RecordedFixtureAdapter`):**
  - Reads `backend/tests/fixtures/recorded/*.json`.
  - Re-normalizes real payloads through `map_apple_item` and `map_bluesky_profile` as `CACHED`.
  - Preserves original capture timestamps.

### 8. Real Negatives Pipeline (`services/sources/capture.py` & `verify_negatives.py`)
- Captures real namesake candidates from Apple and Bluesky into `backend/tests/fixtures/real_negatives/candidates.jsonl`.
- Enforces two-verifier consensus before exporting verified cases to `verified.jsonl`.

---

## Test Suite & Quality Assurance

The test suite contains **683 automated tests** covering every failure matrix cell, edge case, and contract invariant:

```
Test Module                                      Passed
------------------------------------------------ ------
test_apple_source.py                             26
test_bluesky_source.py                           23
test_cache.py                                    10
test_demo_source.py                              2
test_fixture_handoff_coordination.py             11
test_hardening_data_quality.py                   11
test_hardening_fuzz.py (1,000 fuzz iterations)   2
test_hardening_isolation_honesty.py              5
test_hardening_matrix.py (full failure matrix)   482
test_hardening_ratelimit_cancellation.py         7
test_image_fetch.py                              22
test_plumbing.py                                 14
test_prefill.py                                  52
test_real_negatives.py                           5
test_registry_fixtures.py                        11
------------------------------------------------ ------
TOTAL                                            683 passed in ~71s
```

### Running Tests

```powershell
# Run the complete test suite
python -m pytest backend/app/services/sources/tests/ -v

# Run core deliverable tests (Apple, Bluesky, Image Fetch, Prefill)
python -m pytest backend/app/services/sources/tests/test_apple_source.py backend/app/services/sources/tests/test_bluesky_source.py backend/app/services/sources/tests/test_image_fetch.py backend/app/services/sources/tests/test_prefill.py -v

# Run linter
python -m ruff check backend/app/services/sources/ backend/app/services/image_fetch.py

# Run formatter check
python -m ruff format --check backend/app/services/sources/ backend/app/services/image_fetch.py
```

---

## File Manifest & Ownership Boundaries

All Person 3 deliverables are strictly contained within authorized paths:

```
backend/
├── app/
│   └── services/
│       ├── image_fetch.py               # Safe image fetch & pHash
│       └── sources/
│           ├── __init__.py              # Package exports
│           ├── apple.py                 # Apple iTunes Search API adapter
│           ├── base.py                  # SourceAdapter protocol
│           ├── bluesky.py               # Bluesky public AppView adapter
│           ├── cache.py                 # Caching & InMemoryCacheFake
│           ├── capture.py               # Real namesake capture tool
│           ├── demo.py                  # Compatibility re-exports
│           ├── errors.py                # Error code & status mapping
│           ├── fixtures_demo.py         # Offline simulated fixture adapter
│           ├── fixtures_recorded.py     # Offline recorded replay adapter
│           ├── http.py                  # Safe HTTP client wrapper
│           ├── not_connected.py         # Null adapters for unsupported sources
│           ├── outcome.py               # SourceResult builders
│           ├── prefill.py               # Safe URL prefill parser
│           ├── ratelimit.py             # Leaky-bucket rate limiter
│           ├── registry.py              # Central 9-source registry
│           ├── spike.py                 # Hour-1 spike verification runner
│           ├── text.py                  # Bio link & text extraction
│           ├── verify_negatives.py      # Dual-verifier CLI & validation
│           └── tests/                   # 683 automated unit/integration tests
├── tests/
│   └── fixtures/                        # Real & simulated test fixtures
└── docs/
    └── SPIKE_RESULTS.md                 # Hour-1 spike findings & verification
```

**Zero modifications** were made outside these authorized paths (Person 2 routes, Person 4 scoring, and Person 5 database models remain untouched).
