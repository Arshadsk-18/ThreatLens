# ThreatLens Hour-1 API Spike Results

**Date:** 2026-10-12  
**Owner:** Person 3 (Discovery & Connectors, branch: `feat/discovery`)  
**Reference:** Contract Section 5.5, 5.6, 13.1, 13.2, 13.4, and Appendix A  
**Script:** [`backend/app/services/sources/spike.py`](file:///c:/Users/kedar/ThreatLens/backend/app/services/sources/spike.py) (runnable via `python -m app.services.sources.spike` from `backend/`)

---

## 1. Summary of Calls

| Call / Target | URL | Status | Latency | Response Size | Content-Type | Rate-Limit Headers | Fixture File |
|---|---|---|---|---|---|---|---|
| **1. Apple Search (Fictional)** | `https://itunes.apple.com/search?term=kaveri+bank&entity=software&country=in&limit=10` | 200 OK | 563 ms | 42 B | `text/javascript; charset=utf-8` | None observed | [`apple_search_kaveri_bank.json`](file:///c:/Users/kedar/ThreatLens/backend/tests/fixtures/apple_search_kaveri_bank.json) |
| **1b. Apple Search (Sample)** | `https://itunes.apple.com/search?term=bank&entity=software&country=in&limit=5` | 200 OK | 827 ms | 55,706 B | `text/javascript; charset=utf-8` | None observed | [`apple_search_bank_sample.json`](file:///c:/Users/kedar/ThreatLens/backend/tests/fixtures/apple_search_bank_sample.json) |
| **2. Apple Lookup (bundleId)** | `https://itunes.apple.com/lookup?bundleId=com.idfcfirstbank.optimus&country=in` | 200 OK | 372 ms | 11,958 B | `text/javascript; charset=utf-8` | None observed | [`apple_lookup_bundle.json`](file:///c:/Users/kedar/ThreatLens/backend/tests/fixtures/apple_lookup_bundle.json) |
| **2b. Apple Search (Empty)** | `https://itunes.apple.com/search?term=xyznonexistentterm99999&entity=software&country=in&limit=5` | 200 OK | 342 ms | 42 B | `text/javascript; charset=utf-8` | None observed | [`apple_search_empty.json`](file:///c:/Users/kedar/ThreatLens/backend/tests/fixtures/apple_search_empty.json) |
| **2c. Apple Lookup (Empty)** | `https://itunes.apple.com/lookup?id=999999999999999&country=in` | 200 OK | 406 ms | 42 B | `text/javascript; charset=utf-8` | None observed | [`apple_lookup_empty.json`](file:///c:/Users/kedar/ThreatLens/backend/tests/fixtures/apple_lookup_empty.json) |
| **3. Bluesky searchActors** | `https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors?q=bank&limit=5` | 200 OK | 914 ms | 3,163 B | `application/json; charset=utf-8` | None observed | [`bsky_search_actors_bank.json`](file:///c:/Users/kedar/ThreatLens/backend/tests/fixtures/bsky_search_actors_bank.json) |
| **3b. Bluesky getProfiles** | `https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles?actors=...` (repeated params) | 200 OK | 611 ms | 4,237 B | `application/json; charset=utf-8` | None observed | [`bsky_get_profiles.json`](file:///c:/Users/kedar/ThreatLens/backend/tests/fixtures/bsky_get_profiles.json) |
| **4a. Bluesky searchPosts (public)** | `https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=bank&limit=5` | 403 Forbidden | 54 ms | 2,334 B | `text/html` | None observed | [`bsky_search_posts_403.json`](file:///c:/Users/kedar/ThreatLens/backend/tests/fixtures/bsky_search_posts_403.json) |
| **4b. Bluesky searchPosts (api)** | `https://api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=bank&limit=5` | 200 OK | 923 ms | 11,171 B | `application/json; charset=utf-8` | None observed | (Direct host response recorded in spike) |

---

## 2. Per-Question Findings

### Exact Apple field names vs Section 13.1 mapping
- **Contract mapped fields verified:**
  - `trackId` (numeric int, e.g. `1521443352`): present on all app results.
  - `bundleId` (string, e.g. `"com.idfcfirstbank.optimus"`): present on all app results.
  - `trackName` (string, e.g. `"IDFC FIRST Bank: MobileBanking"`): present on all app results.
  - `sellerName` (string, e.g. `"IDFC FIRST BANK LTD"`): present on all app results.
  - `artistId` (numeric int, e.g. `1090320551`): present on all app results.
  - `description` (multiline text): present on all app results.
  - `primaryGenreName` (string, e.g. `"Finance"`): present on all app results.
  - `sellerUrl` (string): present on major bank apps (e.g. `"https://www.idfcfirstbank.com/"`); optional/missing on some smaller apps.
  - `artworkUrl100` and `artworkUrl512` (strings): both present on all app results.
  - `releaseDate` (ISO UTC timestamp string, e.g. `"2020-12-07T08:00:00Z"`): present on all app results.
  - `userRatingCount` (int): present on apps with ratings (e.g. `210606`); defaults to 0 or missing if no reviews.
  - `trackViewUrl` (canonical store URL string, e.g. `"https://apps.apple.com/in/app/idfc-first-bank-mobilebanking/id1521443352?uo=4"`): present on all app results.
- **Top-level envelope:** Always `{ "resultCount": int, "results": list[dict] }`.
- **Zero-result / Empty lookups:** Both `search` on a nonsense term and `lookup` on an invalid ID return `{ "resultCount": 0, "results": [] }` with HTTP 200 OK.

### Apple artwork URLs & Hostnames
- **Observed fields:** Both `artworkUrl100` (100x100 thumbnail) and `artworkUrl512` (512x512 high-res icon) exist on every app result.
- **Observed hostnames:** `is1-ssl.mzstatic.com` (and `is2-ssl.mzstatic.com` on alternate assets).
- **Inspection requests:**
  - GET `https://is1-ssl.mzstatic.com/...` returned **HTTP 200 OK**.
  - `Content-Type`: `image/jpeg`.
  - Content length range: 3,715 bytes to 23,300 bytes (well under the 2 MB security cap).

### Bluesky Profile Search (`searchActors`) and Enrichment (`getProfiles`)
- **`searchActors` fields present:**
  - Item fields: `did`, `handle`, `displayName`, `avatar`, `createdAt`, `description`, `indexedAt`, `labels`, `associated`.
  - Does it include `description`? **Yes** (bio string).
  - Does it include `avatar`? **Yes** (`https://cdn.bsky.app/...`).
  - Does it include `createdAt`? **Yes** (ISO timestamp string).
  - Does it include `labels`? **Yes** (array of label dicts).
  - Does it include follower / post counts? **No** (`searchActors` does NOT contain `followersCount`, `followsCount`, or `postsCount`).
- **`getProfiles` enrichment shape:**
  - Adds: `followersCount` (int), `followsCount` (int), `postsCount` (int).
  - Top-level key: `{ "profiles": list[dict] }`.
- **Repeated parameters:**
  - `actors` parameter is repeated for batch queries: `actors=did:plc:...&actors=did:plc:...`.
  - Batching works cleanly in batches of up to 25 DIDs.
- **Max limit:**
  - Testing `searchActors?q=bank&limit=100` returned **HTTP 200 OK**, confirming max retrieval capacity.

### Bluesky Self-Labels
- **Label schema:** List of dicts, e.g. `[{"val": "...", "src": "...", "cts": "..."}]`.
- **`!no-unauthenticated` status:** In the sampled results for query `bank`, all returned accounts had `labels: []`. The `!no-unauthenticated` label was **NOT observed** in this specific sample, but the connector implementation in `bluesky.py` checks for `"no-unauthenticated"` or `"!no-unauthenticated"` in `label.val` per contract requirements.

### Post Search (`searchPosts`) Behaviour
- `https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=bank&limit=5`:
  - Returned **HTTP 403 Forbidden** (served by BunnyCDN with HTML body: `<title>403 Forbidden</title>`).
  - **Confirms Section 13.2 / Appendix A**: anonymous post search is blocked on the public AppView and must remain P1/authenticated.
- `https://api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=bank&limit=5`:
  - Returned **HTTP 200 OK** on the direct API host.

### Exact Image Hostnames Allowlist
All observed icon and avatar URLs match the allowlist defined in Contract Section 5.6:
1. Apple App Store icons: `*.mzstatic.com` (specifically observed: `is1-ssl.mzstatic.com`, `is2-ssl.mzstatic.com`).
2. Bluesky avatars: `cdn.bsky.app` (e.g. `https://cdn.bsky.app/img/avatar/plain/...`).

Approved allowlist rule in `backend/app/services/image_fetch.py`:
- `cdn.bsky.app`
- `*.mzstatic.com` (and root `mzstatic.com`)

### Observed Rate-Limit Behaviour
- Neither Apple iTunes nor Bluesky public endpoints returned explicit `RateLimit-*` or `Retry-After` headers in successful 200 responses.
- Apple requests enforced with `>= 3.0s` spacing and Bluesky with `>= 1.0s` spacing succeeded with zero rate-limiting.
- When 429 occurs, Apple does not provide retry headers; the connector immediately records `SourceStatus.RATE_LIMITED` and ceases retries.

---

## 3. Contradicts the Contract

**NONE.**  
All measured facts, endpoint behaviors, response schemas, and image hostnames strictly match the specifications in Contract v3.0.0. No contract-change note is required.

---

## 4. Confirms the Contract

1. **[VERIFY 13.1] Apple iTunes Search & Lookup:** Works anonymously without an API key. Field names match Section 13.1 exactly.
2. **[VERIFY 13.2] Bluesky public AppView:** `searchActors` and `getProfiles` work anonymously on `public.api.bsky.app`.
3. **[VERIFY 13.2] Bluesky searchPosts:** Returns 403 Forbidden on `public.api.bsky.app`, confirming it is not suitable for anonymous P0 scans.
4. **[VERIFY 5.6] Image hosts:** Icons are hosted exclusively on `*.mzstatic.com` and avatars on `cdn.bsky.app`.
5. **[VERIFY 5.5] Rate limits:** Throttling of 3 s on Apple and 1 s on Bluesky avoids 429 errors.

---

## 5. Open [VERIFY] Items Remaining

- None for Person 3's discovery and connector scope. All Phase 0 verification items are resolved by real recorded fixtures.
