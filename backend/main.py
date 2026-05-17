"""
LexGuard — AI-Powered Contract Intelligence Platform
=====================================================

Main FastAPI application with security middleware, rate limiting,
and comprehensive error handling.

Google Cloud Services Used:
- Google Gemini 2.5 (Multi-Agent Adversarial LLM)
- Google Document AI (PDF/Document Parsing)
- Google Cloud Vision API (OCR for Images)
- Google Cloud Translation API (Multi-language Support)
- Google Cloud Natural Language API (Sentiment/Entity Analysis)
- Google Vertex AI Embeddings (RAG / Semantic Search)
- Google Cloud Firestore (Results Database)
- Google Cloud Storage (Document Storage)
- Google Cloud Run (Containerized Deployment)
- Firebase Hosting (Frontend)
"""
import time
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.routers.analyze import router as analyze_router


# ============================================================
# APPLICATION
# ============================================================
app = FastAPI(
    title="LexGuard API",
    description="AI-Powered Adversarial Contract Intelligence Platform. "
                "Uses multi-agent debate (Corporate Lawyer vs Consumer Advocate vs Judge) "
                "with RAG-enhanced legal knowledge base to analyze contracts.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================
# SECURITY: CORS with restricted origins
# ============================================================
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "https://lexguard.web.app",
    "https://lexguard.firebaseapp.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ============================================================
# SECURITY: Rate Limiting Middleware
# ============================================================
RATE_LIMIT_REQUESTS = 10  # max requests per window
RATE_LIMIT_WINDOW = 60    # window in seconds
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple in-memory rate limiter to prevent abuse."""
    if request.url.path == "/api/analyze":
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        # Clean old entries
        _rate_limit_store[client_ip] = [
            t for t in _rate_limit_store[client_ip] if now - t < RATE_LIMIT_WINDOW
        ]
        if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please wait before trying again."},
            )
        _rate_limit_store[client_ip].append(now)
    return await call_next(request)


# ============================================================
# SECURITY: Response Headers Middleware
# ============================================================
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


# ============================================================
# ROUTES
# ============================================================
app.include_router(analyze_router)


@app.get("/")
async def root():
    """Root endpoint with API information and Google services documentation."""
    return {
        "name": "LexGuard",
        "tagline": "AI Rights & Contract Intelligence System",
        "description": (
            "Adversarial multi-agent AI that analyzes contracts to detect "
            "exploitative clauses, hidden liabilities, and real-world risks."
        ),
        "version": "1.0.0",
        "endpoints": {
            "analyze": "POST /api/analyze — Upload and analyze a contract",
            "report": "POST /api/report/pdf — Generate downloadable PDF report",
            "health": "GET /api/health — Service health check",
            "docs": "GET /docs — Interactive API documentation",
        },
        "agents": [
            "Agent 1: Corporate Lawyer (Defense)",
            "Agent 2: Consumer Rights Advocate (Prosecution)",
            "Agent 3: Neutral Judge (Verdict & Scoring)",
            "Agent 4: Plain English Translator (Simplification)",
            "Agent 5: Scenario Simulator (Consequence Modeling)",
            "Agent 6: Negotiation Advisor (Strategy & Alternatives)",
        ],
        "google_services": [
            "Google Gemini 2.5 Flash/Pro (Multi-Agent Adversarial LLM)",
            "Google Vertex AI Embeddings (RAG / Semantic Similarity)",
            "Google Document AI (PDF/Document Parsing)",
            "Google Cloud Vision API (OCR for Images)",
            "Google Cloud Translation API (Multi-language Support)",
            "Google Cloud Natural Language API (Sentiment & Entity Analysis)",
            "Google Cloud Firestore (Results Database)",
            "Google Cloud Storage (Document Storage)",
            "Google Cloud Run (Containerized Deployment)",
            "Firebase Hosting (Frontend)",
        ],
    }
