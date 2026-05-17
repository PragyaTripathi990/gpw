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
                 │  Risk Scoring + Report   │
                 │  Stored in Firestore     │
                 └──────────────────────────┘
```

## 🔧 Google Cloud Services Used (14)

| # | Service | Purpose |
|---|---------|---------|
| 1 | **Gemini 2.5 Pro** | Multi-agent adversarial analysis |
| 2 | **Gemini 2.5 Flash** | Clause segmentation & simplification |
| 3 | **Google Document AI** | Premium PDF/document parsing |
| 4 | **Cloud Vision API** | OCR for images of contracts |
| 5 | **Cloud Translation API** | Multi-language contract support |
| 6 | **Cloud Natural Language** | Sentiment & entity analysis |
| 7 | **Cloud Storage** | Store uploaded documents |
| 8 | **Firestore** | Store analysis results |
| 9 | **Cloud Run** | Backend deployment |
| 10 | **Firebase Hosting** | Frontend deployment |
| 11 | **Firebase Auth** | User authentication |
| 12 | **BigQuery** | Analytics on analyzed contracts |
| 13 | **Google Docs API** | Report export |
| 14 | **Google Sheets API** | Data export |

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
- **Adversarial Debate**: 4 AI agents debate each clause from different perspectives
- **Risk Scoring**: Per-clause and overall risk scores (1-10)
- **Plain English**: Every clause translated to simple language anyone can understand
- **Suggested Fixes**: AI-generated fairer alternatives for risky clauses
- **Beautiful Dashboard**: Interactive visualization of all findings

## 👥 Team

Built at [Hackathon Name] 2025
