# FactGuard AI: Real-Time Web Intelligence & Fact Verification

> A high-performance, real-time fact-checking system that verifies arbitrary claims against live web sources (DuckDuckGo + Wikipedia), re-ranks evidence with cross-encoders, and validates statements using LLM reasoning (Groq / Llama-3).

---

## System Architecture

```
                       [ Next.js Frontend ]
                        (Port 3000 / UI)
                               │
                       HTTP POST /api/verify
                       HTTP GET /api/analytics
                               ▼
                       [ FastAPI Backend ]
                        (Port 8000 / API)
                               │
                  ┌────────────┴────────────┐
                  ▼                         ▼
         [ Claim Extractor ]      [ Web Intelligence ]
           (SpaCy parsing)         (DuckDuckGo + Wiki)
                  │                         │
                  └────────────┬────────────┘
                               ▼
                    [ CrossEncoder Reranker ]
                               │
                               ▼
                   [ LLM Verification Chain ]
                     (Groq / Llama-3 / RAG)
                               │
                               ▼
               [ Verdict + Reasoning + Citations ]
```

---

## Features

- **Real-Time Web Intelligence**: Fetches authentic context, debunking reports, and encyclopedic evidence directly from DuckDuckGo and Wikipedia on the fly.
- **Direct Source Citations**: Each retrieved piece of evidence includes article title, snippet, source publisher pill, and a direct clickable URL.
- **Intelligent Claim Extraction**: Uses SpaCy dependency parsing to isolate atomic verifiable claims from complex statements.
- **Neural Re-ranking**: Scores retrieved web context with a Cross-Encoder model (`ms-marco-MiniLM-L6-v2`) to prioritize relevant facts.
- **LLM Reasoning**: Nuanced validation with transparent rationale and confidence scoring via Groq (`llama-3.1-8b-instant`).
- **Analytics & Telemetry**: Real-time performance dashboard featuring latency trendlines, verdict distributions, and cache metrics.
- **Persistent LRU Cache**: Instant sub-second responses for previously analyzed claims.

---

## Tech Stack

### Backend
- **Framework**: FastAPI (Uvicorn)
- **NLP**: SpaCy (`en_core_web_md`)
- **Neural Re-ranker**: Sentence Transformers (`cross-encoder/ms-marco-MiniLM-L6-v2`)
- **Web Intelligence**: DuckDuckGo + Wikipedia REST API
- **LLM**: Groq API (`llama-3.1-8b-instant`)

### Frontend
- **Framework**: Next.js (App Router, TypeScript)
- **Styling**: Vanilla CSS Modules (Glassmorphism & Dark Mode)
- **Icons**: Lucide React
- **Visualization**: Recharts

---

## Quick Start

### 1. Backend Setup

```bash
# From project root, activate python environment
python -m venv .venv
.\.venv\Scripts\activate  # Linux/macOS: source .venv/bin/activate

# Install requirements
pip install -r backend/requirements.txt

# Start FastAPI application
python backend/main.py
```
> Server runs on `http://127.0.0.1:8000`.

#### Optional: Configure Groq API Key
Add your Groq API key in `backend/.env` for automated AI verdicts:
```env
GROQ_API_KEY=your_groq_api_key_here
PORT=8000
```

---

### 2. Frontend Setup

Open a new terminal:
```bash
cd frontend

# Install UI dependencies
npm install

# Run the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

### 3. CLI Verification Tool

You can also fact-check claims directly from the command line:
```bash
python backend/cli.py "The Great Wall of China is visible from the Moon."
```
