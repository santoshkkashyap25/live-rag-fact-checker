# FactGuard AI: Real-Time Web Intelligence & Fact Verification

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16.2+-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**An open-source, real-time fact-checking system that verifies arbitrary claims against live web intelligence (DuckDuckGo + Wikipedia), re-ranks evidence with Cross-Encoders, and generates verifiable verdicts using LLM reasoning.**

[Features](#-key-features) • [Quick Start](#-quick-start) • [CLI Tool](#-cli-fact-checker) • [Scope & Limitations](#️-system-scope--honest-limitations) • [Contributing](#-contributing) • [License](#-license)

</div>

---

## 🎯 Project Motivation

Information moves faster than human verification pipelines can keep up. Most automated fact-checking systems rely on **static databases** or pre-scraped knowledge graphs that quickly become obsolete. 

**FactGuard AI** explores a **live Retrieval-Augmented Generation (RAG)** approach: when presented with a claim, the system dynamically queries the open web (Wikipedia + DuckDuckGo), neural re-ranks the most contextually relevant snippets using a transformer-based Cross-Encoder, and prompts an LLM with strict few-shot verification guidelines to synthesize an objective verdict with transparent source citations.

---

## ✨ Key Features

- **🌐 Live Internet Intelligence**: Queries DuckDuckGo and Wikipedia on the fly. No stale static databases.
- **🔑 Bring Your Own Key (BYOK) Engine**: Plug in custom API keys for **Groq**, **Google Gemini**, **OpenAI**, or **Anthropic Claude** directly from the UI, or fallback seamlessly to the system's default key.
- **🔒 Zero-Storage Client Privacy**: Custom keys are stored only in the browser's `localStorage` (`factguard_llm_config`) and transmitted via headers per-request—never stored on server disk or database.
- **🔗 Direct Source Citations**: Every piece of evidence includes publisher badges (`Wikipedia`, `DuckDuckGo`) and direct clickable external links (`Read Source Article ↗`).
- **🧠 Cross-Encoder Re-Ranking**: Uses `cross-encoder/ms-marco-MiniLM-L6-v2` to score semantic relevance against the extracted claim.
- **🤖 Multi-Provider LLM Reasoning**: Fast verification reasoning powered by native Groq execution or `litellm` (OpenAI, Gemini, Claude) with structured JSON output validation.
- **⚡ In-Memory & Disk LRU Cache**: Instant (`0.00s`) responses for recurring claims with per-user isolation and auto-disk persistence.
- **📊 Real-Time Analytics Dashboard**: Live system monitoring featuring response time trendlines, verdict distributions, and confidence histograms.
- **💻 CLI Tooling**: Standalone command-line interface (`backend/cli.py`) for headless terminal verification and scripting.
- **🐳 Production Ready**: Fully Dockerized with multi-stage builds and pre-baked model weights for zero-delay container startup.

---

## 🚀 Quick Start

### Option A: Docker Compose (Recommended)

The easiest way to run the entire stack locally with all dependencies pre-configured:

```bash
# 1. Clone the repository
git clone https://github.com/your-username/llm-fact-checker.git
cd llm-fact-checker

# 2. Configure your Groq API key in backend/.env
cp backend/.env.example backend/.env
# Edit backend/.env and set GROQ_API_KEY=gsk_...

# 3. Build and launch containers
docker compose up -d --build
```

- **Frontend Application**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

To view container logs or stop services:
```bash
# Stream live logs
docker compose logs -f

# Stop and clean up containers
docker compose down
```

---

### Option B: Bare-Metal Setup

#### 1. Backend Setup

Prerequisites: **Python 3.11+**

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies (CPU PyTorch recommended)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and enter your GROQ_API_KEY

# Start backend server
python main.py
```
> The API will be available at `http://127.0.0.1:8000`.

#### 2. Frontend Setup

Prerequisites: **Node.js 20+** and **npm**

```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```
> The web interface will be available at `http://localhost:3000`.

---

### Option C: CLI Fact-Checker

You can verify statements directly in your command line without starting the web UI:

```bash
# From project root (with virtualenv activated):
python backend/cli.py "Bananas are naturally radioactive due to potassium-40."
```

**Example Output:**
```text
======================================================================
FactGuard AI - Fact Verification
======================================================================
Claim: Bananas are naturally radioactive due to potassium-40.
----------------------------------------------------------------------
VERDICT:    True
CONFIDENCE: 99.0%
REASONING:  All evidence sources explicitly state that bananas naturally 
            contain radioactive potassium-40 isotopes, confirming the claim.
----------------------------------------------------------------------
RETRIEVED EVIDENCE (3 items):
  [1] [score: 10.12] [Wikipedia] Potassium-40 in natural foods
      URL: https://en.wikipedia.org/wiki/Potassium-40
  [2] [score: 9.84]  [DuckDuckGo] Are bananas radioactive? - EPA Science
      URL: https://www.epa.gov/radtown/natural-radioactivity-food
======================================================================
```

---

## 🛡️ System Scope & Honest Limitations

> **Fact-checking automated with AI is a research assistant, not an absolute arbiter of truth.**

FactGuard AI is designed around transparency and verifiable grounding rather than ungrounded generative authority.

### What FactGuard AI Does Well
- **Fast Web Grounding**: Retrieves current, open-web facts in ~3–5 seconds without maintaining a costly or stale vector database.
- **Auditable Evidence**: Every claim verdict includes direct publisher source pills, relevancy scores, and clickable reference URLs so human users can audit the original reporting.
- **Atomic Claim Extraction**: Isolates key verifiable assertions from compound or convoluted conversational statements using SpaCy dependency parsing.
- **Strict Rationale**: Guided few-shot LLM prompts minimize ungrounded hallucinations by requiring explicit evidence corroboration.

### Boundaries & Known Limitations
- **Consensus & Search Quality**: Verdicts reflect the consensus and quality of top search results. If credible sources are absent or unindexed, the system marks claims as *Unverifiable*.
- **Not a Substitute for Human Investigation**: Complex historical debates, emerging breaking crises, nuanced political speeches, and medical decisions require domain-expert human scrutiny.
- **Public API Rate Limits**: Real-time web retrieval relies on public DuckDuckGo and Wikipedia REST interfaces. High-volume unthrottled queries may be subject to temporary IP rate limits.
- **Satire & Sarcasm Sensitivity**: Deeply sarcastic statements or satirical publications (e.g., *The Onion*) may occasionally fool semantic retrievers if context is ambiguous.
- **Always Audit Sources**: While low temperature (`0.2`) and strict output schemas reduce errors, LLMs can occasionally misinterpret complex propositions. Always click through to the provided source URLs.

---

## 🤝 Contributing

Contributions are warmly welcomed! To contribute:

1. **Fork** the repository.
2. Create a feature branch: `git checkout -b feature/amazing-feature`.
3. Commit your changes: `git commit -m 'Add amazing feature'`.
4. Push to the branch: `git push origin feature/amazing-feature`.
5. Open a **Pull Request**.

Please ensure new code adheres to existing formatting standards and includes appropriate tests.

---

## 📄 License

This project is distributed under the **MIT License**. See the [LICENSE](./LICENSE) file for complete details.
