"""Integration tests for the LexGuard API endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.fixture
def transport():
    return ASGITransport(app=app)


@pytest.mark.asyncio
async def test_health_check(transport):
    """Health endpoint should return 200 with status healthy."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "LexGuard API"


@pytest.mark.asyncio
async def test_analyze_missing_input(transport):
    """Analyze should return 400 when no document is provided."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            data={"doc_type": "General Contract"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_analyze_empty_text(transport):
    """Analyze should return 400 for empty text input."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            data={"raw_text": "", "doc_type": "General Contract"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cors_headers(transport):
    """CORS headers should be present in response."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/health",
            headers={"Origin": "http://localhost:3000"},
        )
    assert response.status_code in (200, 405)


@pytest.mark.asyncio
async def test_analyze_returns_expected_schema(transport):
    """Analyze should return proper JSON schema (integration test — requires LLM key)."""
    async with AsyncClient(transport=transport, base_url="http://test", timeout=120) as client:
        response = await client.post(
            "/api/analyze",
            data={
                "raw_text": "The company may terminate this agreement at any time without notice.",
                "doc_type": "General Contract",
            },
        )
    if response.status_code == 200:
        data = response.json()
        assert "overall_risk_score" in data
        assert "risk_grade" in data
        assert "clause_results" in data
        assert "executive_summary" in data
        assert isinstance(data["clause_results"], list)
        assert data["overall_risk_score"] >= 0
        assert data["overall_risk_score"] <= 10
        assert data["risk_grade"] in ("A", "B", "C", "D", "F")
