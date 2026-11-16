# FactGuard AI: Academic Gold-Standard Benchmark Report (N = 288)

**Evaluation Environment**:
- **Dataset**: `tests/data/claims_test_1000.json` (288 balanced claims across 25 scientific & empirical domains)
- **Class Proportions**: 40.0% True, 40.0% False, 20.0% Unverifiable (FEVER, SciFact, Climate-FEVER, TruthfulQA)
- **Model Engine**: Groq LPU (`qwen/qwen3.8-27b`, temp = 0.2)
- **Retrieval Engine**: Multi-Source Concurrent Async Engine (`httpx`, Wikipedia extracts, DuckDuckGo HTML/Lite)
- **Evidence State**: 100% Frozen Disk Cache (`tests/data/frozen_evidence_1000.json`, zero search drift)

---

## 1. Primary Benchmark Results

| System / Configuration | Accuracy | 95% Wilson Score CI | Coverage | Selective Accuracy | False Positives | p50 Latency | ECE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **84.7%** | **[80.1% – 88.4%]** | **78.8%** | **91.2%** | **0 (0.0%)** | **12.27s** | **0.0697** |
| Baseline: Raw Search + LLM | 77.8% | [72.6% – 82.2%] | 72.2% | 89.4% | 0 (0.0%) | 12.16s | 0.0891 |
| Baseline: Ungrounded Zero-Shot | 59.7% | [54.0% – 65.2%] | 46.2% | 93.2% | 0 (0.0%) | 12.29s | 0.1303 |

---

## 2. Paired Statistical Significance Tests (McNemar with Continuity Correction)

### FactGuard AI vs. Ungrounded Zero-Shot LLM
* **Contingency Matrix**:
  - Both Correct: `148`
  - FactGuard Only Won: `96`
  - Ungrounded Only Won: `24`
  - Both Wrong: `20`
* **Discordant Pairs**: `120`
* **Chi-Square Statistic ($\chi^2$)**: `42.0083`
* **p-value**: `p = 0.0`
* **Statistical Significance**: **Statistically Significant at p < 0.01**

### FactGuard AI vs. Raw Web Search Baseline
* **Contingency Matrix**:
  - Both Correct: `215`
  - FactGuard Only Won: `29`
  - Raw Search Only Won: `9`
  - Both Wrong: `35`
* **Discordant Pairs**: `38`
* **Chi-Square Statistic ($\chi^2$)**: `9.5`
* **p-value**: `p = 0.002055`
* **Statistical Significance**: **Statistically Significant at p < 0.01**

---

## 3. Calibration & Safety Guarantees

* **Expected Calibration Error (ECE)**: `0.0697`.
* **Safety**: Zero false positive inversions (0 of 288 claims). FactGuard prioritizes epistemic abstention over unverified assertions.
