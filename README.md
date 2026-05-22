# FactGuard AI: Decoupled Fact-Checking System

> A fact-checking system using Retrieval-Augmented Generation (RAG) to verify claims against a trusted knowledge base, split into a FastAPI backend and a Next.js frontend.

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
         [ Claim Extractor ]       [ Hybrid Search DB ]
           (SpaCy parsing)          (FAISS + BM25)
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
               [ Verdict + Reasoning + Evidence ]
```

---

## Features

- **Decoupled Architecture**: Fast Python API backend running FastAPI and a highly responsive React frontend in Next.js.
- **Intelligent Claim Extraction**: Uses SpaCy dependency parsing to isolate verifiable claims from complex statements.
- **Hybrid Semantic Search**: Integrates FAISS (vector similarity search with Sentence Transformers) and BM25 (lexical search) for robust evidence retrieval.
- **Re-ranked Evidence**: Utilizes a Cross-Encoder re-ranker model to prioritize retrieved facts.
- **LLM Verification**: Nuanced validation using HuggingFace / Groq LLMs with transparent reasoning and cited sources.
- **Analytics Dashboard**: Real-time performance telemetry featuring latency trendlines, verdict distributions, and cache hit metrics.
- **Optimized Caching**: LRU query cache with TTL expiration.

---

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Web Server**: Uvicorn
- **NLP / Embedding**: SpaCy, Sentence Transformers (`all-MiniLM-L6-v2`)
- **Vector Index**: FAISS (IndexFlatL2 + IndexIDMap)
- **BM25 Search**: Rank-BM25
- **LLM Service**: Groq (`llama-3.1-8b-instant`) / LangChain

### Frontend
- **Framework**: Next.js (App Router, TypeScript)
- **Styling**: Vanilla CSS Modules (Glassmorphism & Dark Mode)
- **Icons**: Lucide React
- **Visualization**: Recharts

---

## Setup & Quick Start

### 1. Prerequisites
- Python 3.9+
- Node.js 18+

### 2. Backend Setup
Navigate to the `backend/` directory:
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

Create a `.env` file inside the `backend/` folder:
```env
GROQ_API_KEY=your_groq_api_key_here
ENABLE_SCRAPING=false
```

Build the FAISS vector database from facts source CSV:
```bash
python build_database.py
```

Start the FastAPI application:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup
Open a new terminal session and navigate to the `frontend/` directory:
```bash
cd frontend

# Install UI dependencies
npm install

# Run the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to access the application.
