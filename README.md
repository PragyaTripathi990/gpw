# LexGuard

**AI-Powered Adversarial Contract Intelligence Platform**

Analyze contracts for exploitative clauses using a multi-agent debate architecture powered by Gemini 2.5. Upload PDFs, DOCX, images, URLs, or raw text in any language --- LexGuard extracts clauses, runs adversarial analysis, and produces explainable risk scores with fair alternative suggestions.

**[Live Demo](https://lexguard-frontend-712213214076.us-central1.run.app/)**

---

## Architecture

```
User Input (PDF / DOCX / Image / URL / Text)
                |
                v
    +--- Document Pipeline ---+
    |                          |
    v                          v
Google Document AI       Cloud Vision OCR
    |                          |
    +-------> Cloud Translation API
                    |
                    v
            Clause Extraction
            (Firestore + Cloud Storage)
                    |
                    v
    +--- 4-Agent Debate System ---+
    |       |        |        |
    v       v        v        v
 Lawyer  Consumer  Judge  Translator
 Agent   Advocate  Agent    Agent
    |       |        |        |
    +-------+--------+--------+
                |
                v
        Risk Scoring Engine
        (Adaptive Triaging +
         Deterministic Fallback)
                |
                v
        Explainable Report
        (Risk Scores + Fair Alternatives)
```

## How It Works

### 1. Document Ingestion
- **PDFs/DOCX**: Parsed via Google Document AI for structured text extraction
- **Images**: Cloud Vision OCR for text recognition
- **Multilingual**: Cloud Translation API normalizes all input to English for analysis
- **Storage**: Raw documents in Cloud Storage, extracted clauses in Firestore

### 2. Adversarial Multi-Agent Analysis
Four specialized agents debate each clause:

| Agent | Role |
|---|---|
| **Lawyer Agent** | Identifies legal risks, flags ambiguous language, checks regulatory compliance |
| **Consumer Advocate** | Detects exploitative terms, unfair conditions, hidden obligations |
| **Judge Agent** | Weighs arguments, assigns final risk score, resolves conflicts |
| **Translator Agent** | Ensures multilingual inputs are accurately interpreted in context |

### 3. Risk Scoring
- **Adaptive clause triaging**: High-risk clauses get deeper multi-agent analysis; low-risk clauses use deterministic scoring
- **Explainable output**: Every risk score includes reasoning from each agent
- **Fair alternatives**: Generates rewritten clause suggestions that balance both parties

## Key Features

| Feature | Details |
|---|---|
| Multi-format Input | PDF, DOCX, images, URLs, raw text |
| Multilingual Support | Auto-translation via Cloud Translation API |
| 4-Agent Debate | Adversarial analysis for balanced risk assessment |
| Adaptive Triaging | Reduces inference cost by routing low-risk clauses to deterministic scoring |
| Explainable Scoring | Per-clause reasoning with agent attribution |
| Fair Alternatives | AI-generated balanced clause rewrites |

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python, FastAPI |
| **AI** | Gemini 2.5 Pro/Flash |
| **Document Processing** | Google Document AI, Cloud Vision OCR |
| **Translation** | Google Cloud Translation API |
| **Database** | Firestore |
| **Storage** | Google Cloud Storage |
| **Frontend** | Next.js |
| **Deployment** | Cloud Run, Firebase Hosting |

## Setup

### Prerequisites
- Python 3.10+
- Google Cloud project with enabled APIs (Document AI, Vision, Translation, Firestore)
- Gemini API key

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add GCP credentials + Gemini key
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Deployment

- **Backend**: Deployed on Google Cloud Run
- **Frontend**: Firebase Hosting
- **Live**: [lexguard-frontend-712213214076.us-central1.run.app](https://lexguard-frontend-712213214076.us-central1.run.app/)

## License

MIT
