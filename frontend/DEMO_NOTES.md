# ThreatLens Rehearsal & Live Demo Guide (§18.1)

> **Crucial Timing & Cold-Start Reminder:**
> **Warm up the backend 5 minutes before the demo!**
> If deployed on a platform with container cold starts (e.g. Render, Railway, Fly.io, Cloud Run), send an HTTP GET request to `/api/v1/health` or `/api/v1/brands` to warm up memory and pre-populate DB pools.

---

## 1. Quick Rehearsal Overview (3-Minute Script)

| Time | Step | Screen / Route | What It Proves | Track Voice Rule |
|---|---|---|---|---|
| **0:00–0:20** | **Brand Profile & Prefill** | `/brand` | Exact ID ground truth; instant App Store link parsing. | State: *"We anchor all forensic detection to cryptographic and store-verified identifiers, never names."* |
| **0:20–1:00** | **Track A: DEMO Scan** | `/scan` & `/scan/:id` | Detection funnel arithmetic invariant; honest `NOT_CONNECTED` source disclosure. | **MANDATORY:** State aloud: *"Track A uses simulated positives."* Badged `SIMULATED`. |
| **1:00–1:25** | **Cleared Assets Registry** | `/cleared` | Proves official assets and benign namesakes are never flagged (both 30% criteria). | State: *"Official apps cleared by exact ID (R1) and developer ID (R2). Namesakes cleared by Gates G4/G5."* |
| **1:25–2:05** | **Evidence Compare** | `/findings` & `/findings/:id` | Multi-signal breakdown; character-level name diff; pHash icon distance; corroboration gates. | **MANDATORY:** Say *"candidate for review"*, never *"fake"*, *"scam"*, or *"malicious"*. |
| **2:05–2:35** | **Track B: LIVE Scan & Graceful Failure** | `/scan` & `/sources` | Real Apple/Bluesky queries; graceful handling of rate limits and catalog outages. | **MANDATORY:** State: *"Real catalog queries; graceful degraded state instead of deceptive empty clean passes."* |
| **2:35–3:00** | **Evaluation Lab** | `/evaluation` | Scientific rigour; Wilson 95% intervals; zero official false positives (`official_flagged_count = 0`). | State: *"Honesty is the feature. Metrics are computed dynamically on the frozen HELDOUT split."* |

---

## 2. Step-by-Step Click Path & Spoken Talking Points

### Step 1 (0:00–0:20): Brand Profile & Prefill
- **Where to click:**
  1. Open top or sidebar navigation to **Brand Profile** (`/brand`).
  2. Point to the active brand card: *"Kaveri Bank"*.
  3. Click **"Register Official Asset"** button in header.
  4. In the dialog, paste the App Store URL:
     ```text
     https://apps.apple.com/us/app/kaveri-mobile-plus/id1524312345
     ```
  5. Click **"Fetch Metadata"**.
  6. Show judges how the metadata populates: Display Name (*"Kaveri Bank"*), Stable Identifier (*"1524312345"*), Category (*"Finance"*), Publisher (*"Kaveri Bank Ltd"*).
  7. Close the dialog.
- **What to say aloud:**
  > *"Every forensic finding in ThreatLens begins with registered ground truth. Instead of fuzzy search, we register stable store IDs and developer IDs. Watch how pasting a real App Store link instantly populates verified metadata."*

---

### Step 2 (0:20–1:00): Track A — DEMO Scan Execution
- **Where to click:**
  1. Click **Scan Setup** (`/scan`).
  2. Click **DEMO Mode** card (note the purple `SIMULATED` badge).
  3. Show the source coverage list below:
     - Notice **Google Play Catalog**, **Instagram Graph API**, and **X API v2** are clearly badged `NOT_CONNECTED` with honest copy: *"Not connected. Requires platform API access. Not queried."*
  4. Click **"Launch DEMO Scan"**.
  5. Watch the 7-stage deterministic progress bar cycle through `resolving_brand` → `fetching` → `normalizing` → `hashing_images` → `assessing` → `completed` (100%).
  6. Inspect the **Detection & Filtering Funnel**:
     - Point out the Invariant Note:
       `60 (deduplicated) = 5 (cleared) + 29 (not relevant) + 14 (benign lookalike) + 0 (below threshold) + 12 (findings)`
- **What to say aloud:**
  > *"Track A uses simulated positives to rehearse offline forensic inspection. Notice our honest coverage: Instagram, X, and Google Play are marked NOT_CONNECTED rather than pretending they were scanned clean. The funnel strictly enforces mathematical invariant arithmetic — every retrieved item is accounted for."*

---

### Step 3 (1:00–1:25): Cleared Assets Registry
- **Where to click:**
  1. Click **Cleared Assets** (`/cleared`) in the sidebar, or click the header pill in Findings.
  2. Point out **Rule R1_EXACT_ID**: Official app cleared because bundle ID matches `com.kaveribank.mobile`.
  3. Click the **Official Publisher ID** tab:
     - Point out **Rule R2_PUBLISHER_ID**: *"Published by the registered developer. Consider registering this app."*
  4. Click the **Benign Lookalike** tab:
     - Point out **Gate G4**: *"Similar name, unrelated category, no corroborating evidence."* (Score capped at 24).
     - Point out **Gate G5**: *"Declared unofficial in its bio. Not verified. Disclaimers can be copied by impersonators; an analyst may reopen this."* with the orange badge *"Declared unofficial, not verified"*.
- **What to say aloud:**
  > *"This screen proves the two 30% rubric criteria: official assets are never flagged. R1 clears exact bundle IDs; R2 clears secondary apps by the same developer. Meanwhile, Gate G4 silences unrelated namesakes like coffee roasters, and Gate G5 isolates declared parody accounts while warning analysts that bio disclaimers can be spoofed."*

---

### Step 4 (1:25–2:05): Evidence Compare of "Kaveri Bank Rewards"
- **Where to click:**
  1. Navigate to **Findings Queue** (`/findings`).
  2. Point out the candidate list: scores sorted descending.
  3. Click the row for **Kaveri Bank Rewards** (Risk score 72 / 100).
  4. Arrive on **Finding Detail & Evidence Compare** (`/findings/f1000000-0000-0000-0000-000000000001`).
  5. Show the risk breakdown:
     - *Name Lexical Similarity*: +25 pts
     - *Visual Perceptual Hash (93% similarity)*: +30 pts
     - *Content / Keyword Lure*: +17 pts
     - *Total*: 72 / 100 (HIGH).
  6. Point to the **Forensic Name Diff**:
     - Visual character tokens displaying `Kaveri Bank` in official green vs `Rewards` addition in candidate amber.
  7. Show **Corroborating Groups**:
     - *"Visual, Content, Context. The name group never counts as corroboration."*
  8. Click **"Record Decision"** dialog:
     - Show that reasons are mandatory for audit compliance.
- **What to say aloud:**
  > *"We treat look-alikes as candidates for review, presenting objective evidence rather than sensational accusations. Here is Kaveri Bank Rewards. The name group alone never corroborates — our pipeline requires visual pHash similarity and lure keywords before escalating severity. Notice the character-level diff and the exact points audit."*

---

### Step 5 (2:05–2:35): Track B — LIVE Scan & Graceful Failure
- **Where to click:**
  1. Go to **Scan Setup** (`/scan`).
  2. Select **LIVE Mode** (badged green `LIVE`).
  3. Show that demo fixtures are prohibited and unselectable.
  4. View a live scan result or inspect `/scan/scan-demo-001`:
     - Show the `bluesky_public` card badged `Rate limited`.
     - Read the copy: *"Stopped after 4 of 6 queries; partial results kept."*
  5. Visit **Source Coverage** (`/sources`):
     - Show the status pill `RATE_LIMITED / ERROR` with transparent limits note.
- **What to say aloud:**
  > *"In Track B, we query live provider catalogs. When a platform enforces rate limits or drops a connection, ThreatLens never reports a silent, false 'zero findings clean scan'. It clearly badges the provider as Rate Limited and preserves partial queries."*

---

### Step 6 (2:35–3:00): Evaluation Lab — Scientific Rigour
- **Where to click:**
  1. Navigate to **Evaluation Lab** (`/evaluation`).
  2. Read the permanent header: *"Honesty is the feature (§14). Positives are synthetic; negatives are real captured namesakes labelled by the team. Small sample, see intervals."*
  3. Review the headline metrics:
     - Precision, Recall, F1, and False-Positive Rate each accompanied by strict **Wilson 95% Confidence Intervals** (e.g. `[0.82, 0.98]`).
     - Point to **"Official Assets Flagged: 0 (PASS)"**.
  4. Show the **Confusion Matrix**: TP, FP, TN, FN.
  5. Show the **Ablation Study Table**:
     - Compare `FULL` pipeline against `NO_IDENTITYGUARD` and `NO_GATES` to demonstrate the exact false-positive drop achieved by our architecture.
  6. Point out the **Audited Failure Cases**:
     - Open analysis of where the pipeline abstains or errs.
- **What to say aloud:**
  > *"We conclude with our core differentiator: radical honesty. We do not claim 99% accuracy. Every metric is computed dynamically on the frozen HELDOUT benchmark split with Wilson confidence intervals. Our official flagged count is zero. Component ablations prove that IdentityGuard and corroboration gates eliminate alert fatigue."*

---

## 3. Strict Vocabulary & Voice Rules (§15.3 & §18.1)

| Forbidden Word / Phrase | Correct ThreatLens Copy | Reason |
|---|---|---|
| ❌ "Fake app" | ✅ "Look-alike candidate" / "Candidate for review" | Forensic objectivity; names can deceive. |
| ❌ "Scam" / "Scammer" | ✅ "Suspected look-alike" / "Unverified namesake" | We report observable signals, not judicial claims. |
| ❌ "Malicious" | ✅ "Candidate with high visual/name similarity" | Avoid speculative intent before analyst review. |
| ❌ "Phishing attack" | ✅ "Credential lure keywords observed" | Exact observable forensic signal. |
| ❌ "100% safe" / "Legitimate" | ✅ "Cleared by Rule R1 / Exact ID Match" | Safety cannot be proven without exact identity anchors. |
| ❌ "99% accuracy" | ✅ "Precision 0.92 [0.81, 0.97] on HELDOUT" | Scientific rigour requires confidence intervals. |

---

## 4. Rehearsal Checklist Prior to Stage Presentation

- [x] Run `npm run build` — confirm clean build with route-level code splitting under 500kB.
- [x] Verify no API keys or secrets in `dist/` bundles.
- [x] Run `npm run test` (Vitest) — 90 of 90 unit tests pass.
- [x] Run `npx playwright test` — all E2E rehearsal flows pass (DEMO story + LIVE failure path).
- [ ] Ping `/api/v1/health` 5 minutes prior to live stage presentation to warm container caches.
- [ ] Ensure browser viewport is at least 1280×800 to display the complete side-by-side Evidence Compare layout.
