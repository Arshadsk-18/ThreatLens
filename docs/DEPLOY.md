# ThreatLens Deployment Guide & Database Operations (Section 21)

**Owner:** Person 2 (Deployment Lead)  
**Database Contributor:** Person 5 (Database, Persistence, Seed & QA)

---

## 1. Database Configuration (Supabase PostgreSQL)

### 1.1 Connection String & Driver
- **Pooled Connection String:** Use the Supabase PgBouncer pooled connection string on port `5432` (Session mode):
  ```bash
  DATABASE_URL="postgresql+psycopg2://<user>:<password>@<pooler-host>:5432/<dbname>?sslmode=require"
  ```
- **Driver:** Uses `psycopg2` via `postgresql+psycopg2://`. If provided with `postgres://`, `app.db.session.get_engine_options` automatically normalizes it to `postgresql://`.
- **SSL Requirement:** SSL is mandatory (`sslmode=require`). `app.db.session.create_db_engine()` automatically configures `connect_args={"sslmode": "require"}` for all PostgreSQL URLs.

### 1.2 Table Initialization (`create_all` on First Start)
- The database schema is fully managed via SQLAlchemy 2.0 portable models (`app.db.models`).
- In your FastAPI application lifespan (`app/main.py`), call `init_db()` on startup:
  ```python
  from contextlib import asynccontextmanager
  from fastapi import FastAPI
  from app.db.session import init_db, create_db_engine, mark_interrupted_scans, SessionLocal

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # 1. Initialize tables if not existing
      engine = create_db_engine()
      init_db(engine)

      # 2. Mark any scans interrupted by server restart as FAILED
      with SessionLocal() as session:
          interrupted_count = mark_interrupted_scans(session)
          if interrupted_count:
              print(f"Marked {interrupted_count} interrupted scan(s) as FAILED")

      yield
  ```

### 1.3 Seeding the Demo Story Once After Deploy
- Once the service is running, run the idempotent seed script once:
  ```bash
  python -m app.db.seed.seed
  ```
- This populates Brand **Kaveri Bank**, its 4 registered official assets, and 60 candidate fixtures matching Appendix B with the complete demo assessment story.
- Detailed instructions and API verification steps are in `backend/app/db/seed/run_seed.md`.

---

## 2. Server Constraints (Section 21)

- **Workers:** Pin `--workers 1` in your start command (`uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`). In-process provider rate limiters and background asyncio tasks require a single worker per instance.
- **Cold Starts:** Ping `/api/v1/health` 5 minutes prior to live presentations to ensure free-tier container instances and database poolers are warm.
