# ThreatLens v3 — Deployment Guide

**Contract Version:** `3.0.0` · **API Prefix:** `/api/v1`
**Single Source of Truth:** `docs/ARCHITECTURE_API_CONTRACT.md`, Section 21
**Owner:** Person 2 (Backend/API & Integration Lead), in coordination with Person 5 (Database & Seed)

---

## 1. Hosting Architecture Overview

| Component | Target Platform | Runtime / Config | Start Command / Output |
|---|---|---|---|
| **Backend API** | Render (Web Service) | Python 3.12, root `backend/` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| **Database** | Supabase PostgreSQL | Pooled connection (Supavisor port 6543, SSL required) | SQLAlchemy connection pool |
| **Frontend** | Vercel | Node 20+, root `frontend/` | `npm run build` -> `dist`, SPA rewrite via `vercel.json` |

> [!IMPORTANT]
> **One worker, one instance constraint:** Scan jobs run as in-process `asyncio` tasks and provider rate limiters are in-process. Never horizontally scale backend workers or instances. Exactly `--workers 1` is required.

---

## 2. Environment Variables

### Backend Configuration (Render Environment)

| Variable | Required? | Example / Value | Description |
|---|---|---|---|
| `PYTHON_VERSION` | Yes | `3.12.0` | Pinned Python runtime on Render |
| `DATABASE_URL` | Yes | `postgresql://postgres.[ref]:[pw]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require` | Supabase pooled connection string. Must use SSL. |
| `CORS_ORIGINS` | Yes | `["https://threatlens.vercel.app"]` | Exact frontend origins (JSON array or comma-separated). **No wildcard `*` allowed in production.** |
| `APPLE_COUNTRY` | Yes | `in` | Apple iTunes store country storefront (default `in`) |
| `CACHE_TTL_SECONDS` | Yes | `3600` | Provider response cache TTL in seconds (1 hour) |
| `SCAN_TIMEOUT_SECONDS`| Yes | `90` | Whole-scan abort timeout in seconds |
| `LLM_API_KEY` | Optional | *(leave blank)* | Optional P1 capability (executive summaries) |
| `LLM_MODEL` | Optional | *(leave blank)* | Optional P1 capability |
| `BLUESKY_APP_PASSWORD`| Optional | *(leave blank)* | Optional P1 authenticated post search |
| `BLUESKY_HANDLE` | Optional | *(leave blank)* | Optional P1 authenticated post search |

### Frontend Configuration (Vercel Environment)

| Variable | Value | Notes |
|---|---|---|
| `VITE_API_URL` | `https://threatlens-api.onrender.com` | Base URL of deployed backend. **Zero secrets in `VITE_*`.** |

> [!CAUTION]
> Ensure `.env` is never committed to Git. `.env.example` contains safe placeholders. Service-role database keys must remain strictly backend-only.

---

## 3. Render Backend Deployment Steps

### Method A: Blueprint Deployment (Automated via `render.yaml`)
1. Push repository changes to GitHub (`main` branch).
2. In the Render Dashboard, click **New +** -> **Blueprint**.
3. Connect the `ThreatLens` repository. Render automatically reads `render.yaml`.
4. Fill in the two unsynced environment variables:
   - `DATABASE_URL`: Your Supabase pooled PostgreSQL URL with `?sslmode=require`.
   - `CORS_ORIGINS`: Your Vercel frontend URL, e.g. `["https://threatlens.vercel.app"]`.
5. Click **Apply**. Render builds and starts the service.

### Method B: Manual Web Service Setup
1. In Render Dashboard, click **New +** -> **Web Service**.
2. Connect your Git repository.
3. Configure the following settings:
   - **Name:** `threatlens-api`
   - **Root Directory:** `backend`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
   - **Plan:** `Free`
   - **Health Check Path:** `/api/v1/health`
4. Under **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.12.0`
   - `DATABASE_URL`: `postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require`
   - `CORS_ORIGINS`: `["https://threatlens.vercel.app"]`
   - `APPLE_COUNTRY`: `in`
   - `CACHE_TTL_SECONDS`: `3600`
   - `SCAN_TIMEOUT_SECONDS`: `90`
5. Click **Deploy Web Service**.

---

## 4. Supabase PostgreSQL Setup & Coordination with Person 5

1. **Create Supabase Project:**
   - Create a free project in Supabase.
   - Go to **Project Settings** -> **Database** -> **Connection String**.
   - Select **Connection pooling** (Supavisor) and mode **Transaction** (port `6543`).
   - Copy the URI and append `?sslmode=require`.
2. **Schema & Migration Coordination (with Person 5):**
   - Tables are created on first startup using SQLAlchemy `create_all()`.
   - **Never destructively reset or drop deployed tables.**
   - Run Person 5's seed script once after initial deployment to populate default brand data (e.g. Kaveri Bank official assets).

---

## 5. Vercel Frontend Deployment Steps

1. In Vercel Dashboard, click **Add New...** -> **Project**.
2. Import the `ThreatLens` GitHub repository.
3. In Project Settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Under **Environment Variables**, add:
   - `VITE_API_URL`: Your deployed Render backend URL (e.g. `https://threatlens-api.onrender.com`).
5. `vercel.json` in the root repository automatically configures SPA routing rewrites:
   ```json
   {
     "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
   }
   ```
6. Click **Deploy**.

---

## 6. Verified Free-Tier Limits & Operational Constraints

Real free-tier parameters have been verified and documented:

| Provider | Constraint / Limit | Operational Impact | Mitigation |
|---|---|---|---|
| **Render (Free Tier)** | Spins down after 15 minutes of zero traffic. | First request experiences **30 to 60-second cold start latency**. | **Warm-up procedure:** Ping `/api/v1/health` 5 minutes before the demo and immediately at the start. |
| **Render (Free Tier)** | Ephemeral filesystem (no persistent local disk). | Any local SQLite file is erased on restart or spin-down. | Deployed backend uses Supabase PostgreSQL for persistence. |
| **Render (Free Tier)** | 512 MB RAM, 0.1 shared vCPU, 750 free hours/mo. | Memory-efficient single worker execution. | `--workers 1`, concurrency bounded via semaphores. |
| **Supabase (Free Tier)** | 500 MB database storage, pauses after 7 days inactivity. | Sufficient for demo and evaluation runs. | Use pooled connection port 6543 to avoid connection exhaustion. |
| **Apple iTunes Search** | ~20 requests / minute per IP. | High burst query plans can trigger HTTP 429. | Query budget of 8 per scan, 3 s inter-query spacing, 1-hour cache, honest `RATE_LIMITED` status. |
| **Vercel (Hobby)** | 100 GB bandwidth / month. | Pure static SPA bundle; well within limits. | Types generated ahead of time with zero runtime compilation. |

---

## 7. Restart Safety & Scan Recovery

Per Section 21 restart safety requirements:
- When the backend process starts (or recovers from a sleep/crash cycle), the lifespan startup hook runs `recover_running_scans()`.
- Any scan left in `RUNNING` or `QUEUED` state is automatically marked `FAILED` with the exact message:
  `"Interrupted by server restart"`
- This ensures the UI never displays an indefinitely spinning scan.

---

## 8. Local Run, Tunnel Backup & Fallback Video Guide

### Plan A: Deployed Cloud Infrastructure
- Backend on Render (`https://threatlens-api.onrender.com`)
- Frontend on Vercel (`https://threatlens.vercel.app`)

### Plan B: Local Execution with Cloudflare Tunnel / ngrok (Live Backup)
If Render sleeps or experiences network latency during the presentation:
1. Start local backend:
   ```powershell
   cd backend
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. Expose via Cloudflare Tunnel or ngrok:
   ```powershell
   # Cloudflare Tunnel
   cloudflared tunnel --url http://127.0.0.1:8000
   # OR ngrok
   ngrok http 8000
   ```
3. Update `VITE_API_URL` or use local frontend (`npm run dev` at `http://localhost:5173`).

### Plan C: Fallback Video (3-Minute Rehearsed Recording)
Per Section 18.1, record a complete 3-minute video covering:
- **0:00–0:20:** Brand Profile & App Store prefill lookup.
- **0:20–1:00:** Track A DEMO scan (`SIMULATED` badging, funnel invariant, unconnected sources).
- **1:00–1:25:** Cleared view (official app cleared by exact ID, second app by developer ID, namesakes).
- **1:25–2:05:** Evidence Compare side-by-side view (name diff, signals, gates).
- **2:05–2:35:** Track B LIVE scan on a real brand with honest timestamps.
- **2:35–3:00:** Evaluation Lab (HELDOUT metrics with intervals).

---

## 9. Verification Smoke Test Results

All deployment smoke and readiness tests pass locally against the unified contract:

```text
tests/test_deploy_smoke.py ........                                      [100%]
============================== 8 passed in 0.47s ==============================
```

### Verified Checks:
1. `GET /api/v1/health` -> HTTP 200, `{"status": "ok", "service": "threatlens-api", "version": "3.0.0", "contract_version": "3.0.0"}`
2. `GET /api/v1/ready` -> HTTP 200, `{"ready": true, "checks": {"database": "ok", "config": "ok"}}`, zero credentials or connection strings exposed.
3. `GET /api/v1/meta` -> HTTP 200, 20 contract enums, 6 scoring thresholds, 3 supported platforms.
4. `GET /api/v1/sources/status` -> HTTP 200, 9 fixed sources with Google Play, Instagram, X, and Facebook marked `NOT_CONNECTED`.
5. `DEMO Scan` -> HTTP 202 -> 200, 0 network calls, all findings tagged `SIMULATED`.
6. `LIVE Apple Scan` -> HTTP 202 -> 200, real timestamped records, `source_mode=LIVE`.
7. `Funnel Invariant` -> `deduplicated == official_cleared + not_relevant + benign_lookalike + below_threshold + findings` strictly holds.
8. `CORS & Security` -> Exact origins enforced, preflight OPTIONS handled, wildcard disallowed in production, `.env` git-ignored.
