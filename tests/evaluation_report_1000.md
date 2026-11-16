# FactGuard AI: Academic Gold-Standard Benchmark Report (N = 351)

**Evaluation Environment**:
- **Dataset**: `tests/data/claims_test_1000.json` (351 balanced claims across 25 scientific & empirical domains)
- **Class Proportions**: 40.0% True, 40.0% False, 20.0% Unverifiable (FEVER, SciFact, Climate-FEVER, TruthfulQA)
- **Model Engine**: Groq LPU (`qwen/qwen3.8-27b`, temp = 0.2)
- **Retrieval Engine**: Multi-Source Concurrent Async Engine (`httpx`, Wikipedia extracts, DuckDuckGo HTML/Lite)
- **Evidence State**: 100% Frozen Disk Cache (`tests/data/frozen_evidence_1000.json`, zero search drift)

---

## 1. Primary Benchmark Results

| System / Configuration | Accuracy | 95% Wilson Score CI | Coverage | Selective Accuracy | False Positives | p50 Latency | ECE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **85.2%** | **[81.1% – 88.5%]** | **77.8%** | **91.9%** | **0 (0.0%)** | **12.25s** | **0.0725** |
| Baseline: Raw Search + LLM | 78.1% | [73.4% – 82.1%] | 71.2% | 90.0% | 0 (0.0%) | 12.16s | 0.0810 |
| Baseline: Ungrounded Zero-Shot | 58.1% | [52.9% – 63.2%] | 43.6% | 94.1% | 0 (0.0%) | 12.26s | 0.1369 |

---

## 2. Paired Statistical Significance Tests (McNemar with Continuity Correction)

### FactGuard AI vs. Ungrounded Zero-Shot LLM
* **Contingency Matrix**:
  - Both Correct: `178`
  - FactGuard Only Won: `121`
  - Ungrounded Only Won: `26`
  - Both Wrong: `26`
* **Discordant Pairs**: `147`
* **Chi-Square Statistic ($\chi^2$)**: `60.1088`
* **p-value**: `p = 0.0`
* **Statistical Significance**: **Statistically Significant at p < 0.01**

### FactGuard AI vs. Raw Web Search Baseline
* **Contingency Matrix**:
  - Both Correct: `262`
  - FactGuard Only Won: `37`
  - Raw Search Only Won: `12`
  - Both Wrong: `40`
* **Discordant Pairs**: `49`
* **Chi-Square Statistic ($\chi^2$)**: `11.7551`
* **p-value**: `p = 0.000607`
* **Statistical Significance**: **Statistically Significant at p < 0.01**

---

## 3. Calibration & Safety Guarantees

* **Expected Calibration Error (ECE)**: `0.0725`.
* **Safety**: Zero false positive inversions (0 of 351 claims). FactGuard prioritizes epistemic abstention over unverified assertions.
