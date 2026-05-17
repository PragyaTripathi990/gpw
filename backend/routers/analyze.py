"""
Analysis Router — Main API endpoints for document analysis.

Endpoints:
    POST /api/analyze   — Upload and analyze a contract document
    POST /api/report/pdf — Generate downloadable PDF risk report
    GET  /api/health     — Service health check

Security:
    - Input validation (file size, text length, URL format)
    - Sanitized error messages (no internal details leaked)
    - Rate limiting handled in main.py middleware
"""
import ipaddress
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from typing import Optional
from urllib.parse import urlparse

from backend.services.document_parser import parse_document
from backend.services.analysis_enrichment import enrich_analysis
from backend.agents.pipeline import analyze_document

router = APIRouter(prefix="/api", tags=["analysis"])
logger = logging.getLogger(__name__)

# Security constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_LENGTH = 50_000           # 50K characters
MAX_URL_LENGTH = 2048
ALLOWED_DOC_TYPES = {
    "General Contract", "Terms of Service", "Employment Contract",
    "Rental Agreement", "NDA / Confidentiality", "Freelancer Agreement",
    "Insurance Policy", "Loan Agreement", "SaaS Agreement",
    "Privacy Policy", "Offer Letter", "Partnership Agreement",
}


def _validate_url(url: str) -> bool:
    """Validate URL format and reject common SSRF targets."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    # Reject credentialed URLs like http://user:pass@example.com.
    if parsed.username or parsed.password:
        return False

    hostname = (parsed.hostname or "").strip().lower().rstrip(".")
    if not hostname:
        return False

    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        return False

    # Common DNS helpers that map directly to local/private IPs.
    if hostname.endswith((".nip.io", ".sslip.io", ".localtest.me")):
        return False

    try:
        ip_addr = ipaddress.ip_address(hostname)
    except ValueError:
        return True

    return not (
        ip_addr.is_private
        or ip_addr.is_loopback
        or ip_addr.is_link_local
        or ip_addr.is_multicast
        or ip_addr.is_reserved
        or ip_addr.is_unspecified
    )


@router.post("/analyze")
async def analyze_contract(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    raw_text: Optional[str] = Form(None),
    doc_type: str = Form("General Contract"),
):
    """Analyze a contract document using the multi-agent adversarial pipeline.
    
    Accepts file upload (PDF, DOCX, images, TXT), URL, or raw text.
    Returns comprehensive risk analysis with per-clause scoring.
    """
    try:
        # --- Input Validation ---
        if doc_type not in ALLOWED_DOC_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid document type. Allowed: {', '.join(sorted(ALLOWED_DOC_TYPES))}")
        
        if not file and not url and not raw_text:
            raise HTTPException(status_code=400, detail="Please provide a file, URL, or text to analyze.")
        
        file_content = None
        filename = None

        if file:
            file_content = await file.read()
            filename = file.filename
            # Validate file size
            if len(file_content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB.")
            # Validate file extension
            if filename:
                ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
                if ext not in ('pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'webp'):
                    raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")
        
        if url:
            if len(url) > MAX_URL_LENGTH:
                raise HTTPException(status_code=400, detail="URL too long.")
            if not _validate_url(url):
                raise HTTPException(status_code=400, detail="Invalid URL format. Must start with http:// or https://")
        
        if raw_text and len(raw_text) > MAX_TEXT_LENGTH:
            raise HTTPException(status_code=400, detail=f"Text too long. Maximum {MAX_TEXT_LENGTH} characters.")
        
        # --- Parse Document ---
        parsed = await parse_document(
            file_content=file_content,
            filename=filename,
            url=url,
            raw_text=raw_text,
        )
        
        if not parsed.get("text"):
            raise HTTPException(status_code=400, detail="Could not extract text from the document.")

        document_text = parsed["text"]
        
        # --- Run Multi-Agent Analysis ---
        analysis = await analyze_document(document_text, doc_type)
        analysis = enrich_analysis(analysis)

        # Add metadata
        analysis["parsing_method"] = parsed.get("method", "unknown")
        analysis["language_info"] = parsed.get("language_info", {"original_language": "en", "was_translated": False})
        analysis["nlp_sentiment"] = {"score": 0, "magnitude": 0, "interpretation": "unavailable"}
        analysis["nlp_entities"] = []
        analysis["gcs_uri"] = ""
        analysis["analysis_id"] = ""

        return JSONResponse(content=analysis)
    
    except HTTPException:
        raise
    except Exception:
        logger.exception("Contract analysis failed")
        raise HTTPException(
            status_code=500,
            detail="Analysis failed due to an internal service error.",
        )


@router.post("/report/pdf")
async def generate_report(request: Request):
    """Generate a downloadable PDF risk report."""
    try:
        from backend.services.pdf_report import generate_pdf_report
        data = await request.json()
        pdf_bytes = generate_pdf_report(data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=LexGuard_Risk_Report.pdf"}
        )
    except Exception:
        logger.exception("PDF generation failed")
        raise HTTPException(
            status_code=500,
            detail="PDF generation failed due to an internal service error.",
        )


@router.get("/health")
async def health_check() -> dict:
    """Return service health status for monitoring and load balancer probes."""
    return {"status": "healthy", "service": "LexGuard API"}
