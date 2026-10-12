"""Pytest configuration and test environment setup."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
import pytest
from fastapi.testclient import TestClient

# Ensure .env from project root is loaded into environment
project_root = Path(__file__).resolve().parents[2]
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Ensure backend and repo root are in sys.path when running pytest
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.main import create_app


@pytest.fixture
def app():
    """Create a clean FastAPI application instance for testing."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a TestClient instance with persistent event loop portal."""
    with TestClient(app) as test_client:
        yield test_client
