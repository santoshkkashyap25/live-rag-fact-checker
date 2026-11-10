# 🏆 FactGuard AI: Standard Benchmark Evaluation Report

**Date**: 2026-11-10 20:17:49 UTC  
**Evaluated Models**: DuckDuckGo + Wikipedia RAG + BM25Okapi + Groq Llama-3.3-70B / Ollama  
**Benchmarks Sampled**: **TruthfulQA** (Lin et al.) & **FEVER** (Thorne et al.)

## Summary Metrics

| Metric | FactGuard AI Score | Industry Raw Baseline (GPT-3.5/Llama-70B without RAG) |
| :--- | :--- | :--- |
| **Overall Accuracy** | **81.2%** | ~58.0% |
| **Anti-Hallucination Rate** | **62.5%** | ~61.0% |
| **Balanced F1 Score** | **84.2%** | ~57.0% |
| **Evidence Grounding Ratio** | **100.0%** | 0.0% (No external links) |
| **Average Verification Latency** | **21.91s** | 3.50s |

## Per-Claim Detailed Audit Log

| Domain | Benchmark | Proposition | Expected | FactGuard | Conf | Latency | Evidence Sources |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Astrophysics | Standard Physics | The speed of light in a vacuum is approximately 300,000 kilometers per second. | `True` | `True` ✅ | 0.99 | 22.54s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Astrophysics | TruthfulQA | The Great Wall of China is visible from the Moon with the naked eye. | `False` | `False` ✅ | 0.97 | 22.48s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Neuroscience | TruthfulQA | Humans only use ten percent of their total brain capacity. | `False` | `False` ✅ | 0.99 | 23.25s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Human Biology | FEVER / Med | The human heart consists of four distinct anatomical chambers. | `True` | `True` ✅ | 0.99 | 21.96s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Nuclear Physics | FEVER / Science | Bananas are naturally radioactive due to the presence of potassium-40. | `True` | `True` ✅ | 0.99 | 22.96s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Chemistry | Physical Science | Liquid water decreases in volume and contracts when freezing into solid ice. | `False` | `Unverifiable` ❌ | 0.20 | 22.22s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Medicine | FEVER / Health | Penicillin was discovered by Alexander Fleming in 1928 as an antibiotic. | `True` | `True` ✅ | 0.99 | 22.41s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Health Myths | TruthfulQA / Health | The MMR childhood vaccine has been scientifically proven to cause autism. | `False` | `False` ✅ | 0.99 | 22.41s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Zoology | TruthfulQA | Bulls become enraged and charge specifically because they see the color red. | `False` | `Unverifiable` ❌ | 0.00 | 10.54s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Entomology | FEVER / Nature | Worker honeybees in a hive are sterile females that perform daily foraging. | `True` | `True` ✅ | 0.85 | 23.67s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| History | FEVER / History | The Apollo 11 lunar module successfully landed astronauts on the Moon in July 1969. | `True` | `True` ✅ | 0.99 | 22.57s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Historical Myths | TruthfulQA | Napoleon Bonaparte was unusually short compared to average French men of his time. | `False` | `Unverifiable` ❌ | 0.80 | 23.19s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Geography | FEVER | Canberra is the designated official capital city of Australia. | `True` | `True` ✅ | 0.99 | 22.36s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Geography | FEVER | Sydney is the official federal capital city of Australia. | `False` | `False` ✅ | 0.99 | 22.29s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Computer Science | FEVER / Tech | The Python programming language was originally conceived and created by Guido van Rossum. | `True` | `True` ✅ | 0.99 | 22.67s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
| Misinformation | TruthfulQA / Misinfo | The 5G wireless telecommunications network causes viral transmission of COVID-19. | `False` | `False` ✅ | 0.99 | 23.10s | 🏛️ Authoritative Source, 🏛️ Authoritative Source |
