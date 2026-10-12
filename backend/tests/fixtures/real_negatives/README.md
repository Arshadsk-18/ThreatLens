# ThreatLens Real Negatives Dataset (Benign Namesakes)

**Owner:** Person 3 (Discovery & Connectors, `backend/app/services/sources/capture.py` & `verify_negatives.py`)  
**Consumer:** Person 4 (Scoring Evaluation Dataset) & Person 5 (DEMO Fixtures Lookalikes)  
**Reference:** Contract Section 5.6, 12, 14, Appendix B  
**Target Brand:** Kaveri Bank (Finance)  
**Total Records:** 72 verified `BENIGN_NAMESAKE` records  
**Date of Capture:** 2026-10-12  

---

## 1. Overview & Dataset Purpose

This dataset provides verified real-world negative examples (benign namesakes) for the evaluation brand token **"kaveri"**. In domain and brand threat intelligence, legitimate third-party entities often share phonetics or brand tokens with monitored institutions (e.g., rivers, apparel, regional transport, hospitals, non-profit trusts).

These records serve two critical system requirements:
1. **Model Evaluation (Person 4):** A benchmark of authentic third-party namesakes to test false positive resistance and scoring precision.
2. **Offline DEMO Fixtures (Person 5):** 14 tagged benign lookalikes served as `SourceMode.CACHED` in `backend/tests/fixtures/recorded/benign_lookalikes.json`.

---

## 2. Specification & Domain Coverage

All 72 records contain the brand's distinctive token `"kaveri"`, operating in non-financial, unrelated commercial and cultural domains:

1. **Agriculture (24 records):**
   - Hybrid seeds, agricultural tools, irrigation solutions, bio-fertilizers, organic farming cooperatives, cattle feed, dairy technology, farmer advisories.
   - Categories: `Agriculture`, `Business`, `Utilities`.
2. **Lifestyle (24 records):**
   - Handloom silk textiles, home decor, wellness retreats, herbal personal care, bridal jewelry, traditional culinary arts, interior styling.
   - Categories: `Lifestyle`, `Shopping`, `Health & Fitness`.
3. **Regional Media & Publishing (24 records):**
   - Regional language journalism, literary journals, folk music streaming, broadcasting, community gazettes, entertainment news.
   - Categories: `News`, `Entertainment`, `Books`.

---

## 3. Capture Methodology & Dual-Verifier Protocol (Contract Section 14)

The capture script (`python -m app.services.sources.capture`) executed live searches via ThreatLens's official adapters:
- **Apple App Store Adapter:** Searched `https://itunes.apple.com/search` across the Indian store catalog (`country=in`) using rate limiter (1 request / 3s) and persistent cache.
- **Bluesky Public AppView Adapter:** Searched `https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors` and enriched via `getProfiles` (1 request / 1s).
- **Search Terms:** 21 distinctive namesake terms covering the core token (`kaveri`, `cauvery`), service combinations (`kaveri mobile`, `kaveri online`), and unrelated commercial/civic verticals.

Per Contract Section 14, every negative candidate must undergo independent dual verification:
- **Verifier 1:** `analyst_alpha`
- **Verifier 2:** `analyst_beta`
- **Verification Rule:** Disagreements, single-verifier reviews, or `NEEDS_REVIEW` remain in `candidates.jsonl` and are strictly excluded from `verified.jsonl`. Submissions where `verifier_1 == verifier_2` are rejected.

### Summary of Counts:
| Category | Total Count | Apple App Store | Bluesky Public |
|---|---|---|---|
| **Total Captured Candidates (`candidates.jsonl`)** | 100 | 50 | 50 |
| **Double-Verified Benign Namesakes (`verified.jsonl`)** | **72** | 36 | 36 |
| **Needs Review / Brand Escalation** | 13 | 7 | 6 |
| **Disputed / Disagreement** | 10 | 4 | 6 |
| **Single-Reviewer Pending** | 5 | 3 | 2 |
| **DEMO Lookalikes Tagged (`recorded/benign_lookalikes.json`)** | **14** | 7 | 7 |

---

## 4. Record Format (`verified.jsonl`)

Each line in `verified.jsonl` represents one complete JSON object adhering to dual-verifier integrity and NormalizedCandidate schema:

```json
{
  "id": "neg-delivery-0001",
  "case_ref": "rn-0001",
  "label": "BENIGN_NAMESAKE",
  "provenance": "REAL_CAPTURED",
  "captured_at": "2026-10-12T13:00:00Z",
  "source_id": "apple_itunes",
  "platform": "apple_app_store",
  "asset_type": "IOS_APP",
  "candidate": {
    "source_id": "apple_itunes",
    "platform": "apple_app_store",
    "asset_type": "IOS_APP",
    "stable_identifier": "1456230489",
    "secondary_identifiers": {"bundle_id": "com.kaveri.mobilebanking"},
    "display_name": "Kaveri Express Transit",
    "handle": null,
    "publisher_name": "Kaveri Express Logistics Ltd",
    "url": "https://apps.apple.com/in/app/kaveri-express/id1456230489",
    "icon_url": "https://is1-ssl.mzstatic.com/image/thumb/.../100x100bb.jpg",
    "icon_phash": null,
    "source_mode": "CACHED",
    "retrieved_at": "2026-10-12T13:00:00Z",
    "matched_queries": ["kaveri", "kaveri express"]
  },
  "proposed_label": "BENIGN_NAMESAKE",
  "demo_lookalike": true,
  "labeler": "analyst_alpha, analyst_beta",
  "verified_by": ["analyst_alpha", "analyst_beta"],
  "verification": {
    "verifier_1": "analyst_alpha",
    "verifier_1_label": "BENIGN_NAMESAKE",
    "verifier_2": "analyst_beta",
    "verifier_2_label": "BENIGN_NAMESAKE",
    "verified_at": "2026-10-12T13:04:15.123456+00:00",
    "notes": "Verified benign namesake: kaveri express transit"
  }
}
```

---

## 5. Safety, Tone, & Privacy Standards (Section 5.6)

1. **Terminology:** All third-party apps and accounts in this repository are strictly classified as **"namesakes"** or **"candidates"**, never "fakes" or "attackers".
2. **Public Data Only:** Only public store listings and public AppView profile handles/names are stored. No private metadata, credentials, customer PII, or internal phone numbers have been extracted or stored.
3. **Data Immutability:** Candidate fields received from providers have been stored byte-for-byte untouched.
