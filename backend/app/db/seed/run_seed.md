# ThreatLens Deployed Database Seed Guide

This document describes how to execute and verify the idempotent demo seed script (`app.db.seed.seed`) once against the deployed PostgreSQL database (Supabase), in collaboration with Person 2 (Deployment Lead).

---

## 1. Exact Execution Command

From the `backend/` directory, run the seed script with the deployed pooled `DATABASE_URL` (SSL required):

```bash
# Set the deployed pooled connection string in your shell (or .env):
export DATABASE_URL="postgresql+psycopg2://<user>:<password>@<pooler-host>:5432/postgres?sslmode=require"

# Run the idempotent seed script
python -m app.db.seed.seed
```

*(On Windows PowerShell:)*
```powershell
$env:DATABASE_URL = "postgresql+psycopg2://<user>:<password>@<pooler-host>:5432/postgres?sslmode=require"
python -m app.db.seed.seed
```

### Expected Console Output:
```text
Successfully loaded ThreatLens Kaveri Bank demo story:
  brand_id: acc79881-46b6-4938-8e2d-d10e5acbcb17
  scan_id: 00000000-0000-4000-8000-000000000001
  total_seeded: 60
  cleared_count: 5
  lookalike_count: 14
  findings_count: 12
  not_relevant_count: 29
```

---

## 2. Idempotence Guarantee

The seed script is strictly idempotent:
- **Brand**: Reuses existing brand if `name == "Kaveri Bank"`.
- **Official Assets**: Keyed on `(brand_id, platform, stable_identifier)`. Updates in-place if existing.
- **Demo Scan**: Preserves fixed UUID `00000000-0000-4000-8000-000000000001`.
- **Candidate Assets**: Uses race-safe `CandidateRepo.upsert` keyed on `(brand_id, platform, stable_identifier)`, preserving decision memory (`analyst_status`, `analyst_reason`).
- **Assessments**: Cleanly refreshed for the demo scan ID.

Running the command multiple times yields the exact same 60 records with zero duplicate key errors.

---

## 3. Post-Deployment Verification via API (with Person 2)

Once the backend is deployed on Render/Railway, execute these curl commands against `$DEPLOYED_API_URL`:

### Step 1: Verify Demo Brand Exists
```bash
curl -s "$DEPLOYED_API_URL/api/v1/brands" | jq '.items[] | select(.name=="Kaveri Bank")'
```
*Expected: Returns Kaveri Bank profile with `demo_brand: true` and brand ID.*

### Step 2: Verify Completed DEMO Scan & Funnel Invariant
```bash
curl -s "$DEPLOYED_API_URL/api/v1/scans/00000000-0000-4000-8000-000000000001" | jq '.status, .funnel'
```
*Expected output:*
```json
"COMPLETED"
{
  "deduplicated": 60,
  "official_cleared": 5,
  "not_relevant": 29,
  "benign_lookalike": 14,
  "below_threshold": 0,
  "findings": 12
}
```
*Invariant check:* `deduplicated == 60 == 5 + 29 + 14 + 0 + 12`.

### Step 3: Verify Findings Queue
```bash
curl -s "$DEPLOYED_API_URL/api/v1/findings" | jq '.total, [.items[].source_mode] | unique'
```
*Expected output: `.total == 12`, all source modes are `"SIMULATED"` or `"CACHED"`.*

### Step 4: Verify Cleared Identity Assets
```bash
curl -s "$DEPLOYED_API_URL/api/v1/brands/<brand_id>/cleared?decision=CLEARED_BY_IDENTITY" | jq '.total, [.items[].rule]'
```
*Expected output: `.total == 5`, rules contain `["R1_EXACT_ID", "R2_PUBLISHER_ID", "R3_PARTNER"]`.*
