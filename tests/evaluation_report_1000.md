# FactGuard AI: Academic Gold-Standard Benchmark Report (N = 203)

**Evaluation Environment**:
- **Dataset**: `tests/data/claims_test_1000.json` (203 balanced claims across 25 scientific & empirical domains)
- **Class Proportions**: 40.0% True, 40.0% False, 20.0% Unverifiable (FEVER, SciFact, Climate-FEVER, TruthfulQA)
- **Model Engine**: Groq LPU (`qwen/qwen3.8-27b`, temp = 0.2)
- **Retrieval Engine**: Multi-Source Concurrent Async Engine (`httpx`, Wikipedia extracts, DuckDuckGo HTML/Lite)
- **Evidence State**: 100% Frozen Disk Cache (`tests/data/frozen_evidence_1000.json`, zero search drift)

---

## 1. Primary Benchmark Results

| System / Configuration | Accuracy | 95% Wilson Score CI | Coverage | Selective Accuracy | False Positives | p50 Latency | ECE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **84.7%** | **[79.1% – 89.0%]** | **79.3%** | **91.3%** | **0 (0.0%)** | **12.15s** | **0.0684** |
| Baseline: Raw Search + LLM | 77.8% | [71.6% – 83.0%] | 72.9% | 89.2% | 0 (0.0%) | 12.05s | 0.0756 |
| Baseline: Ungrounded Zero-Shot | 53.7% | [46.8% – 60.4%] | 37.4% | 96.0% | 0 (0.0%) | 12.26s | 0.1607 |

---

## 2. Paired Statistical Significance Tests (McNemar with Continuity Correction)

### FactGuard AI vs. Ungrounded Zero-Shot LLM
* **Contingency Matrix**:
  - Both Correct: `92`
  - FactGuard Only Won: `80`
  - Ungrounded Only Won: `17`
  - Both Wrong: `14`
* **Discordant Pairs**: `97`
* **Chi-Square Statistic ($\chi^2$)**: `39.6289`
* **p-value**: `p = 0.0`
* **Statistical Significance**: **Statistically Significant at p < 0.01**

### FactGuard AI vs. Raw Web Search Baseline
* **Contingency Matrix**:
  - Both Correct: `152`
  - FactGuard Only Won: `20`
  - Raw Search Only Won: `6`
  - Both Wrong: `25`
* **Discordant Pairs**: `26`
* **Chi-Square Statistic ($\chi^2$)**: `6.5`
* **p-value**: `p = 0.010787`
* **Statistical Significance**: **Trending at p = 0.010787**

---

## 3. Calibration & Safety Guarantees

* **Expected Calibration Error (ECE)**: `0.0684`.
* **Safety**: Zero false positive inversions (0 of 203 claims). FactGuard prioritizes epistemic abstention over unverified assertions.
