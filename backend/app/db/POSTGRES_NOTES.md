# ThreatLens Supabase PostgreSQL Persistence Notes

**Target:** Supabase PostgreSQL 17.11 (aarch64, pooled connection via PgBouncer on AWS ap-south-1).  
**Role:** Person 5 (Database & Persistence Proof).  
**Environment Variable:** `TEST_DATABASE_URL` (pooled connection, SSL required).

---

## 1. Connection String, Dialects & SSL

1. **Protocol Normalization:**
   - Supabase pooled connection strings often default to `postgres://...` or `postgresql://...`.
   - SQLAlchemy 2.0 removed the `postgres://` dialect alias in favor of `postgresql://` (or explicit `postgresql+psycopg2://`).
   - `get_engine_options` in `app/db/session.py` normalizes `postgres://` prefixes to `postgresql://` transparently.
2. **SSL Mode Requirement:**
   - Supabase rejects unencrypted connections.
   - `create_db_engine()` automatically configures `connect_args={"sslmode": "require"}` for all PostgreSQL URLs.
3. **Connection Pooling & PgBouncer:**
   - Port 5432 on `aws-0-*.pooler.supabase.com` runs in **Session mode**, assigning a server connection for the duration of the client connection.
   - `pool_pre_ping=True` is verified to work cleanly, testing connections before checkouts and pruning stale connections dropped by PgBouncer idle timeouts.

---

## 2. Portable Types & Behavior Verification

| Requirement | Behavior on SQLite | Behavior on Supabase Postgres | Parity Status |
|---|---|---|---|
| **`create_all` on first start** | Generates all 10 tables in-memory or on disk. | Successfully creates all 10 tables and indexes in public schema. | **Identical** |
| **UUID strings** | Stored as `VARCHAR(36)` text. | Stored as `VARCHAR(36)` text, preserving exact case and hyphenation. | **Identical** |
| **JSON columns** | Stored as serialized JSON text via `sqlalchemy.JSON`. | Stored as native `json` type via `sqlalchemy.JSON`. Nested dicts/lists round-trip perfectly without stringification. | **Identical** |
| **Timezone-aware UTC** | `UTCDateTime` TypeDecorator parses strings and attaches UTC timezone. | Returned as timezone-aware UTC datetime (`tzinfo=UTC`). No timezone drift. | **Identical** |
| **Unique constraints** | Multi-column UNIQUE constraint on `(brand_id, platform, stable_identifier)` raises `IntegrityError`. | Postgres raises `psycopg2.errors.UniqueViolation` wrapped as `sqlalchemy.exc.IntegrityError`. | **Identical** |
| **`latest_only` query** | Subquery with `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ... DESC)` filters newest assessment. | Window function executes identically on Postgres planner. Produces same single row per candidate. | **Identical** |
| **Foreign Keys & Cascade** | SQLite requires `PRAGMA foreign_keys=ON`. | Enforced natively by PostgreSQL server; cascading deletes clean up child records. | **Identical** |

---

## 3. Findings & Performance Considerations

1. **WAN Latency on Event Appends:**
   - In `test_scan_lifecycle_and_event_capping`, 250 individual sequential calls to `append_event()` (with individual `session.commit()`) over remote WAN connection took ~35 seconds (~140ms per round trip).
   - In production worker processes, batching events or updating progress periodically rather than per event significantly minimizes round-trip overhead.
2. **Transaction Scoping:**
   - Read queries should always use short-lived sessions or explicit transactions so PgBouncer connections do not linger in `idle in transaction` state.
