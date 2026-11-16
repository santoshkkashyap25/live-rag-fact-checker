# FactGuard AI: Academic Gold-Standard Benchmark Report (N = 253)

**Evaluation Environment**:
- **Dataset**: `tests/data/claims_test_1000.json` (253 balanced claims across 25 scientific & empirical domains)
- **Class Proportions**: 40.0% True, 40.0% False, 20.0% Unverifiable (FEVER, SciFact, Climate-FEVER, TruthfulQA)
- **Model Engine**: Groq LPU (`qwen/qwen3.8-27b`, temp = 0.2)
- **Retrieval Engine**: Multi-Source Concurrent Async Engine (`httpx`, Wikipedia extracts, DuckDuckGo HTML/Lite)
- **Evidence State**: 100% Frozen Disk Cache (`tests/data/frozen_evidence_1000.json`, zero search drift)

---

## 1. Primary Benchmark Results

| System / Configuration | Accuracy | 95% Wilson Score CI | Coverage | Selective Accuracy | False Positives | p50 Latency | ECE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **83.4%** | **[78.3% – 87.5%]** | **79.0%** | **90.0%** | **0 (0.0%)** | **12.13s** | **0.0793** |
| Baseline: Raw Search + LLM | 78.7% | [73.2% – 83.3%] | 74.7% | 88.4% | 0 (0.0%) | 12.01s | 0.0877 |
| Baseline: Ungrounded Zero-Shot | 59.7% | [53.5% – 65.5%] | 45.9% | 93.1% | 0 (0.0%) | 12.24s | 0.1504 |

---

## 2. Paired Statistical Significance Tests (McNemar with Continuity Correction)

### FactGuard AI vs. Ungrounded Zero-Shot LLM
* **Contingency Matrix**:
  - Both Correct: `129`
  - FactGuard Only Won: `82`
  - Ungrounded Only Won: `22`
  - Both Wrong: `20`
* **Discordant Pairs**: `104`
* **Chi-Square Statistic ($\chi^2$)**: `33.4712`
* **p-value**: `p = 0.0`
* **Statistical Significance**: **Statistically Significant at p < 0.01**

### FactGuard AI vs. Raw Web Search Baseline
* **Contingency Matrix**:
  - Both Correct: `190`
  - FactGuard Only Won: `21`
  - Raw Search Only Won: `9`
  - Both Wrong: `33`
* **Discordant Pairs**: `30`
* **Chi-Square Statistic ($\chi^2$)**: `4.0333`
* **p-value**: `p = 0.04461`
* **Statistical Significance**: **Trending at p = 0.04461**

---

## 3. Calibration & Safety Guarantees

* **Expected Calibration Error (ECE)**: `0.0793`.
* **Safety**: Zero false positive inversions (0 of 253 claims). FactGuard prioritizes epistemic abstention over unverified assertions.
