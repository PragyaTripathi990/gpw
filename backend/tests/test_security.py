"""Security tests for the LexGuard API."""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.fixture
def transport():
    return ASGITransport(app=app)


@pytest.mark.asyncio
async def test_security_headers_present(transport):
    """All responses should include security headers."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_invalid_doc_type_rejected(transport):
    """Invalid document types should be rejected."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            data={"raw_text": "test clause", "doc_type": "Malicious; DROP TABLE;"},
        )
    assert response.status_code == 400
    assert "Invalid document type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_oversized_text_rejected(transport):
    """Text exceeding max length should be rejected."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            data={"raw_text": "x" * 60_000, "doc_type": "General Contract"},
        )
    assert response.status_code == 400
    assert "too long" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_url_rejected(transport):
    """Invalid URLs should be rejected to prevent SSRF."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            data={"url": "file:///etc/passwd", "doc_type": "General Contract"},
        )
    assert response.status_code == 400
    assert "Invalid URL" in response.json()["detail"]


@pytest.mark.asyncio
async def test_javascript_url_rejected(transport):
    """JavaScript URLs should be rejected."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            data={"url": "javascript:alert(1)", "doc_type": "General Contract"},
        )
    assert response.status_code == 400
