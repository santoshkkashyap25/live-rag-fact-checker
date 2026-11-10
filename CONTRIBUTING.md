# Contributing to FactGuard AI 🤝

Thank you for your interest in contributing to **FactGuard AI**! We welcome contributions ranging from bug fixes, documentation improvements, and evaluation benchmarks to new search retrievers and LLM integrations.

---

## 🛠️ Development Setup

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 20+** & **npm**
- (Optional) **Ollama** for local testing with `gemma4:e2b` or `llama3.2`

### 2. Clone & Environment Setup
```bash
git clone https://github.com/santoshkkashyap25/live-rag-fact-checker.git
cd live-rag-fact-checker

# Backend Virtual Environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements.txt
pip install -e .

# Frontend Setup
cd frontend
npm install
cd ..
```

---

## 🧪 Running Automated Tests

Before submitting a Pull Request, please ensure all automated tests pass:

```bash
# 1. Run core backend test suite (15 tests)
python backend/test_suite.py

# 2. Run Python SDK integration tests (3 tests)
python tests/test_sdk.py

# 3. Test frontend compilation
cd frontend
npm run build
cd ..
```

---

## 💡 Areas Where We'd Love Your Help

- **New Search Retrievers**: Add Google Custom Search, Tavily, or Bing search provider in `backend/core/web_search.py`.
- **RAG Benchmark Evaluation**: Benchmark FactGuard against TruthfulQA, FEVER, or FactTool datasets.
- **Browser Extension Improvements**: Enhance `extension/` with keyboard shortcuts or custom highlight badges.
- **New Local Models**: Add and verify support for new Ollama and HuggingFace local models.

---

## 📋 Pull Request Guidelines

1. Fork the repo and create a feature branch:
   `git checkout -b feature/your-feature-name`
2. Commit your changes with descriptive commit messages following Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`).
3. Push to your branch and submit a PR to `main`.
4. Our GitHub Actions CI will automatically run the backend test suite, SDK tests, and frontend build.

Thank you for helping make automated AI fact-checking transparent and open-source! ⭐

