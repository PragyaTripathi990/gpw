"""
Analysis Router — Main API endpoints for document analysis.
All Google Cloud services are OPTIONAL — app works with just Gemini API key.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional

from backend.services.document_parser import parse_document
from backend.agents.pipeline import analyze_document

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze")
async def analyze_contract(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    raw_text: Optional[str] = Form(None),
    doc_type: str = Form("General Contract"),
):
    try:
        file_content = None
        filename = None

        if file:
            file_content = await file.read()
            filename = file.filename
        
        # Parse the document
        parsed = await parse_document(
            file_content=file_content,
            filename=filename,
            url=url,
            raw_text=raw_text,
        )
        
        if not parsed.get("text"):
            raise HTTPException(status_code=400, detail="Could not extract text from the document.")

        document_text = parsed["text"]
        
        # Run the adversarial multi-agent analysis
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
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "LexGuard API"}
