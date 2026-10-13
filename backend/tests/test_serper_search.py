"""Unit tests for Serper search web collector."""
import pytest
import respx
import httpx
from app.services.providers.search import search_web
from app.services.web_search import search_web as web_search_alias
import app.services.providers.search as search_module


@pytest.mark.anyio
async def test_search_web_not_connected(monkeypatch):
    """When SERPER_API_KEY is unset, search_web returns NOT_CONNECTED."""
    monkeypatch.setattr(search_module, "SERPER_API_KEY", None)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)

    result = await search_web("test query")
    assert result == {"status": "NOT_CONNECTED", "data": []}


@pytest.mark.anyio
async def test_search_web_success(monkeypatch):
    """When SERPER_API_KEY is set and endpoint succeeds, returns LIVE and results."""
    monkeypatch.setattr(search_module, "SERPER_API_KEY", "test-api-key")
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    mock_serper_response = {
        "organic": [
            {
                "title": "Example Title 1",
                "link": "https://example.com/1",
                "snippet": "First snippet here.",
            },
            {
                "title": "Example Title 2",
                "link": "https://example.com/2",
                "snippet": "Second snippet here.",
            },
        ]
    }

    with respx.mock(base_url="https://google.serper.dev") as respx_mock:
        respx_mock.post("/search").respond(
            status_code=200,
            json=mock_serper_response,
        )

        result = await search_web("threat intel")
        assert result["status"] == "LIVE"
        assert len(result["data"]) == 2
        assert result["data"][0] == {
            "title": "Example Title 1",
            "link": "https://example.com/1",
            "snippet": "First snippet here.",
        }


@pytest.mark.anyio
async def test_search_web_http_error(monkeypatch):
    """When Serper returns non-200, returns ERROR status."""
    monkeypatch.setattr(search_module, "SERPER_API_KEY", "test-api-key")
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    with respx.mock(base_url="https://google.serper.dev") as respx_mock:
        respx_mock.post("/search").respond(
            status_code=403,
            json={"message": "Unauthorized"},
        )

        result = await search_web("threat intel")
        assert result == {"status": "ERROR", "data": []}


@pytest.mark.anyio
async def test_search_web_exception(monkeypatch):
    """When httpx raises an exception, returns ERROR with error message."""
    monkeypatch.setattr(search_module, "SERPER_API_KEY", "test-api-key")
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    with respx.mock(base_url="https://google.serper.dev") as respx_mock:
        respx_mock.post("/search").mock(
            side_effect=httpx.ConnectTimeout("Connection timed out")
        )

        result = await search_web("threat intel")
        assert result["status"] == "ERROR"
        assert "error" in result
        assert "timed out" in result["error"].lower()
        assert result["data"] == []


@pytest.mark.anyio
async def test_web_search_alias(monkeypatch):
    """Verify alias imports resolve to the same collector function."""
    assert web_search_alias is search_web
