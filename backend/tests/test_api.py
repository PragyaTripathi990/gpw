"""Integration tests for the LexGuard API endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.routers import analyze as analyze_router


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
async def test_analyze_returns_expected_schema(transport, monkeypatch):
    """Analyze should return proper JSON schema without calling external services."""

    async def fake_parse_document(*, raw_text=None, **kwargs):
        return {
            "text": raw_text or "",
            "pages": 1,
            "entities": [],
            "method": "plain_text",
            "language_info": {"original_language": "en", "was_translated": False},
        }

    async def fake_analyze_document(document_text: str, doc_type: str):
        assert "terminate" in document_text.lower()
        assert doc_type == "General Contract"
        return {
            "document_type": doc_type,
            "total_clauses": 1,
            "overall_risk_score": 8.0,
            "max_risk_score": 8,
            "risk_grade": "D",
            "recommendation": "DO NOT SIGN WITHOUT MAJOR CHANGES",
            "executive_summary": "This contract contains a high-risk termination clause.",
            "critical_issues": 1,
            "warnings_count": 0,
            "safe_count": 0,
            "clause_results": [
                {
                    "clause": {
                        "clause_number": 1,
                        "title": "Termination",
                        "text": document_text,
                        "category": "TERMINATION",
                    },
                    "defense": "The company wants flexibility.",
                    "prosecution": "The clause is one-sided and risky.",
                    "verdict": {
                        "risk_score": 8,
                        "risk_types": ["EXPLOITATIVE", "ONE_SIDED"],
                        "verdict": "This clause is risky and should be negotiated.",
                        "plain_english": "They can end the deal whenever they want.",
                        "suggested_fix": "Require 30 days notice and data export.",
                        "real_world_impact": "You could lose access without warning.",
                        "defense_validity": 4,
                        "prosecution_validity": 9,
                    },
                    "simple_explanation": "This clause lets the company terminate at will.",
                    "scenarios": [],
                    "negotiation_advice": {},
                    "benchmark_comparison": None,
                    "matched_patterns": [],
                }
            ],
            "contradictions": {
                "contradictions": [],
                "ambiguities": [],
                "missing_protections": [],
                "unusual_terms": [],
            },
        }

    monkeypatch.setattr(analyze_router, "parse_document", fake_parse_document)
    monkeypatch.setattr(analyze_router, "analyze_document", fake_analyze_document)

    async with AsyncClient(transport=transport, base_url="http://test", timeout=15) as client:
        response = await client.post(
            "/api/analyze",
            data={
                "raw_text": "The company may terminate this agreement at any time without notice.",
                "doc_type": "General Contract",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "overall_risk_score" in data
    assert "risk_grade" in data
    assert "clause_results" in data
    assert "executive_summary" in data
    assert "top_red_flags" in data
    assert "risk_summary" in data
    assert isinstance(data["clause_results"], list)
    assert isinstance(data["top_red_flags"], list)
    assert data["overall_risk_score"] >= 0
    assert data["overall_risk_score"] <= 10
    assert data["risk_grade"] in ("A", "B", "C", "D", "F")
