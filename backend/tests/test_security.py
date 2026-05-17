"""Security tests for the LexGuard API."""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.routers import analyze as analyze_router


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


@pytest.mark.asyncio
async def test_localhost_url_rejected(transport):
    """Loopback-style hosts should be rejected."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            data={"url": "http://localhost.localdomain/secrets", "doc_type": "General Contract"},
        )
    assert response.status_code == 400
    assert "Invalid URL" in response.json()["detail"]


@pytest.mark.asyncio
async def test_private_dns_helper_url_rejected(transport):
    """Dynamic DNS domains pointing to private IPs should be rejected."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            data={"url": "http://127.0.0.1.nip.io", "doc_type": "General Contract"},
        )
    assert response.status_code == 400
    assert "Invalid URL" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analysis_errors_are_sanitized(transport, monkeypatch):
    """Unexpected failures should not leak internals to clients."""

    async def fake_parse_document(*, raw_text=None, **kwargs):
        return {
            "text": raw_text or "",
            "pages": 1,
            "entities": [],
            "method": "plain_text",
            "language_info": {"original_language": "en", "was_translated": False},
        }

    async def fake_analyze_document(document_text: str, doc_type: str):
        raise RuntimeError("secret token 123")

    monkeypatch.setattr(analyze_router, "parse_document", fake_parse_document)
    monkeypatch.setattr(analyze_router, "analyze_document", fake_analyze_document)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/analyze",
            data={"raw_text": "test clause", "doc_type": "General Contract"},
        )
    assert response.status_code == 500
    assert response.json()["detail"] == "Analysis failed due to an internal service error."
