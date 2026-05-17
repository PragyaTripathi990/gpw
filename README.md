# 🛡️ LEXGUARD — AI Rights & Contract Intelligence System

> **Adversarial multi-agent AI that analyzes contracts to detect exploitative clauses, hidden liabilities, and real-world risks before users agree to them.**

## 🏗️ Architecture

```
User uploads document
        │
        ▼
┌───────────────┐     ┌──────────────────┐     ┌──────────────┐
│ Google Doc AI │     │ Cloud Vision OCR │     │ Cloud Transl │
│ (PDF parsing) │     │ (Image → Text)   │     │ (Multi-lang) │
└───────┬───────┘     └────────┬─────────┘     └──────┬───────┘
        └──────────────────────┼──────────────────────┘
                               ▼
                 ┌──────────────────────────┐
                 │  Clause Segmentation     │
                 │  (Gemini 2.5 Flash)      │
                 └────────────┬─────────────┘
                              ▼
            ╔═══════════════════════════════════╗
            ║  ADVERSARIAL MULTI-AGENT DEBATE   ║
            ║                                   ║
            ║  🏢 Agent 1: Corporate Lawyer     ║
            ║  🛡️ Agent 2: Consumer Advocate     ║
            ║  ⚖️ Agent 3: Neutral Judge         ║
            ║  📝 Agent 4: Plain English         ║
            ║                                   ║
            ║  All powered by Gemini 2.5 Pro    ║
            ╚═══════════════════════════════════╝
                              ▼
                 ┌──────────────────────────┐
                 │ Risk Scoring + Reporting │
                 │ Optional Cloud Storage   │
                 └──────────────────────────┘
```

## 🔧 Cloud Capabilities Used

| # | Service | Purpose |
|---|---------|---------|
| 1 | **Gemini 2.5 Pro** | Multi-agent adversarial analysis |
| 2 | **Gemini 2.5 Flash** | Clause segmentation & simplification |
| 3 | **Google Document AI** | Premium PDF/document parsing |
| 4 | **Cloud Vision API** | OCR for images of contracts |
| 5 | **Cloud Translation API** | Multi-language contract support |
| 6 | **Cloud Storage** | Optional upload persistence |
| 7 | **Firestore** | Optional result persistence |
| 8 | **Cloud Run** | Backend deployment |
| 9 | **Firebase Hosting** | Frontend deployment |

## 🚀 Quick Start

### Backend
```bash
cd lexguard
pip install -r backend/requirements.txt
# Set your environment variables
export GEMINI_API_KEY=your-key
export GOOGLE_CLOUD_PROJECT=your-project
# Run
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
```

### Frontend
```bash
cd lexguard/frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8080" > .env.local
npm run dev
```

## 📸 Features

- **Upload any format**: PDF, DOCX, Images (OCR), URLs, plain text
- **Multi-language**: Automatically detects and translates non-English contracts
- **Adversarial Debate**: 6 expert roles analyze each clause from opposing perspectives
- **Adaptive Deep Review**: Heuristic triage sends only the highest-risk clauses through expensive LLM analysis for faster results
- **Deterministic Fallback**: Rule-based clause scoring keeps the system useful even when external AI services are unavailable
- **Risk Scoring**: Per-clause and overall risk scores (1-10)
- **Top Red Flags**: High-signal issues are ranked for instant review by judges or users
- **Plain English**: Every clause translated to simple language anyone can understand
- **Suggested Fixes**: AI-generated fairer alternatives for risky clauses
- **Benchmark Comparison**: Clauses are compared against known fair contract patterns
- **Beautiful Dashboard**: Interactive visualization of all findings

## 👥 Team

Built for live hackathon judging and contract-risk demos.
