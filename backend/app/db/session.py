"""Database engine, session management, initialization, and startup helpers."""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, create_engine, event, update
from sqlalchemy.orm import Session, sessionmaker

from .base import Base
from .models import Scan

DEFAULT_SQLITE_URL = "sqlite:///./threatlens.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)


def get_engine_options(
    database_url: str | None = None, **engine_kwargs: Any
) -> tuple[str, dict[str, Any]]:
    """Return the resolved database URL and options dictionary."""
    url = database_url or os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)
    connect_args: dict[str, Any] = dict(engine_kwargs.pop("connect_args", {}))

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    if url.startswith("sqlite"):
        connect_args.setdefault("check_same_thread", False)
    elif url.startswith(("postgresql", "postgres")):
        connect_args.setdefault("sslmode", "require")

    options: dict[str, Any] = {
        "pool_pre_ping": True,
        "connect_args": connect_args,
    }
    options.update(engine_kwargs)
    return url, options


def create_db_engine(database_url: str | None = None, **engine_kwargs: Any) -> Engine:
    """Create a configured SQLAlchemy engine from URL.

    - Uses pool_pre_ping=True
    - Enforces SSL args when URL is Postgres (sslmode=require)
    - Sets check_same_thread=False and enables foreign keys for SQLite
    """
    url, options = get_engine_options(database_url, **engine_kwargs)
    eng = create_engine(url, **options)

    if url.startswith("sqlite"):

        @event.listens_for(eng, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return eng


engine: Engine = create_db_engine()

SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    expire_on_commit=False,
)


def init_db(engine_instance: Engine | None = None) -> None:
    """Initialize database tables through create_all on first start."""
    target_engine = engine_instance or engine
    Base.metadata.create_all(bind=target_engine)


def get_session(
    session_factory: sessionmaker[Session] | None = None,
) -> Generator[Session, None, None]:
    """Dependency helper yielding a database session and closing on completion."""
    factory = session_factory or SessionLocal
    session = factory()
    try:
        yield session
    finally:
        session.close()


def mark_interrupted_scans(session: Session | None = None) -> int:
    """Helper that sets any RUNNING scan to FAILED with the restart message.

    Called at startup by Person 2 to ensure scans are not left silently stuck.
    Returns the number of interrupted scans updated.
    """
    should_close = False
    if session is None:
        session = SessionLocal()
        should_close = True

    try:
        now = datetime.now(UTC)
        stmt = (
            update(Scan)
            .where(Scan.status == "RUNNING")
            .values(
                status="FAILED",
                error_message="Interrupted by server restart",
                completed_at=now,
            )
        )
        result = session.execute(stmt)
        session.commit()
        return int(result.rowcount)
    finally:
        if should_close:
            session.close()
