"""
LexGuard — AI-Powered Contract Intelligence Platform
Main FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.analyze import router as analyze_router

app = FastAPI(
    title="LexGuard API",
    description="AI-Powered Adversarial Contract Intelligence Platform",
    version="1.0.0",
)

# CORS — allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(analyze_router)


@app.get("/")
async def root():
    return {
        "name": "LexGuard",
        "tagline": "AI Rights & Contract Intelligence System",
        "description": "Adversarial multi-agent AI that analyzes contracts to detect exploitative clauses, hidden liabilities, and real-world risks.",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "POST /api/analyze",
            "get_analysis": "GET /api/analysis/{id}",
            "health": "GET /api/health",
        },
        "google_services": [
            "Gemini 2.5 Pro (Multi-Agent LLM)",
            "Google Document AI (Parsing)",
            "Cloud Vision API (OCR)",
            "Cloud Translation API (Multi-language)",
            "Cloud Natural Language API (NLP)",
            "Cloud Storage (Document Storage)",
            "Firestore (Results Database)",
            "Cloud Run (Deployment)",
        ]
    }
