"""Application lifecycle, startup seeding, and shutdown management for ThreatLens."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger("threatlens.lifespan")


def run_startup_seeder() -> None:
    """Idempotently initialize database tables and seed Kaveri Bank demo story if DB is empty."""
    from app.db.base import Base
    from app.db.models import Brand
    from app.db.seed import seed_demo_story
    from app.db.session import SessionLocal, engine

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        count = session.query(Brand).count()
        if count == 0:
            logger.info("Empty database detected. Running idempotent startup seeder...")
            seed_demo_story(session_factory=SessionLocal, engine=engine)
            logger.info("Startup seeder successfully populated demo story.")
        else:
            logger.info("Database already contains %d brand(s). Skipping initial seed.", count)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Startup seeder encountered an error or was skipped: %s", exc)
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan context manager for startup and shutdown hooks."""
    # 1. Startup: restart safety hook (Section 21)
    from app.core.memory_store import get_memory_store

    get_memory_store().recover_running_scans()

    # 2. Database initialization and idempotent startup seeding
    run_startup_seeder()

    yield
    # Shutdown hook
