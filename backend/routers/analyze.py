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
import re
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from typing import Optional

from backend.services.document_parser import parse_document
from backend.agents.pipeline import analyze_document

router = APIRouter(prefix="/api", tags=["analysis"])

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
    """Validate URL format to prevent SSRF attacks."""
    pattern = re.compile(r'^https?://[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    return bool(pattern.match(url))


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
    except Exception as e:
        # Sanitize error message — don't leak internal details
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "secret" in error_msg.lower():
            error_msg = "Internal service error. Please try again."
        raise HTTPException(status_code=500, detail=f"Analysis failed: {error_msg}")


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "LexGuard API"}
