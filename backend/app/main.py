"""ThreatLens v3 API Application Entrypoint.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md
"""

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import AppException
from app.core.middleware import (
    RequestIDMiddleware,
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)

logger = logging.getLogger("threatlens.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context manager for startup and shutdown hooks."""
    # 1. Startup: restart safety hook (Section 21)
    # Any scan left in RUNNING status should be marked FAILED on server restart.
    from app.core.memory_store import get_memory_store

    get_memory_store().recover_running_scans()

    # 2. Database initialization and idempotent startup seeding
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
    except Exception as exc:  # noqa: BLE001
        logger.warning("Startup seeder encountered an error or was skipped: %s", exc)
    finally:
        session.close()

    yield
    # Shutdown hook


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="ThreatLens API",
        description="ThreatLens v3 — Digital Risk Protection: Social & App Monitoring",
        version=settings.VERSION,
        openapi_url="/api/v1/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # 1. Request ID tracking middleware
    app.add_middleware(RequestIDMiddleware)

    # 2. CORS configuration (Section 17, 21: exact frontend origins)
    cors_origins = list(settings.CORS_ORIGINS)
    render_origin = "https://threatlens-ui.onrender.com"
    if render_origin not in cors_origins:
        cors_origins.append(render_origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 3. Custom exception handlers for contract error envelope
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 4. Mount API v1 router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
