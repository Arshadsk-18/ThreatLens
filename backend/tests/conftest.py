import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path when running pytest from repository root
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

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
