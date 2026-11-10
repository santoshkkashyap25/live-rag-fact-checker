# FactGuard Python SDK

[![PyPI Version](https://img.shields.io/badge/pypi-v1.0.0-blue.svg)](https://pypi.org/project/factguard/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/santoshkkashyap25/live-rag-fact-checker?style=social)](https://github.com/santoshkkashyap25/live-rag-fact-checker)

> Real-Time Web Intelligence & Multi-LLM Fact-Checking in 3 lines of Python.

---

## ⚡ Installation

```bash
pip install factguard
```

---

## 🚀 Quickstart

```python
from factguard import FactGuard

# Initialize FactGuard (connects to live cloud or your local server)
fg = FactGuard()

# 1. Fact-check any statement
result = fg.verify("Bananas are naturally radioactive due to potassium-40.")

print(f"Verdict: {result.verdict}")          # 'True'
print(f"Confidence: {result.confidence}")    # 0.95
print(f"Reasoning: {result.reasoning}")      # Evidence analysis
print(f"Sources: {result.evidence_sources}") # ['Wikipedia', ...]
print(f"Citations: {result.evidence_urls}")  # ['https://en.wikipedia.org/...']
```

---

## 🔄 Real-Time SSE Streaming

Stream incremental verification phases live into your terminal, CLI, or UI:

```python
for event in fg.stream("The Eiffel Tower is in Berlin."):
    phase = event.get("phase")
    msg = event.get("message")
    print(f"[{phase}] {msg}")
```

---

## 🔗 Create Shareable Permalinks

Turn any verification into a public permalink with dynamic OpenGraph social cards:

```python
result = fg.verify("Water boils at 100 degrees Celsius.")
share_url = fg.share(result)
print(f"Shareable URL: {share_url}")
# Output: https://factguard-1gge.onrender.com/v/a8f2c3
```

---

## 🤖 LangChain & AI Agent Integration

Use FactGuard as an automated ground-truth tool inside LangChain agents:

```python
from langchain.tools import tool
from factguard import FactGuard

fg = FactGuard()

@tool
def fact_check_statement(statement: str) -> str:
    """Verify factual claims using live DuckDuckGo and Wikipedia retrieval."""
    result = fg.verify(statement)
    return f"Verdict: {result.verdict} ({result.confidence*100:.0f}% confidence). Reasoning: {result.reasoning}"
```

---

## ⚙️ Configuration Options

```python
# Connect to your local self-hosted FactGuard instance:
fg = FactGuard(api_url="http://localhost:8000")

# Run with local Ollama or custom model:
fg = FactGuard(
    api_url="http://localhost:8000",
    provider="ollama",
    model="gemma4:e2b"
)
```

---

## 📜 License
MIT License &bull; Created with ❤️ by [Santosh Kashyap](https://github.com/santoshkkashyap25/live-rag-fact-checker)
