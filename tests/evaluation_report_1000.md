# FactGuard AI: Academic Gold-Standard Benchmark Report (N = 209)

**Evaluation Environment**:
- **Dataset**: `tests/data/claims_test_1000.json` (209 balanced claims across 25 scientific & empirical domains)
- **Class Proportions**: 40.0% True, 40.0% False, 20.0% Unverifiable (FEVER, SciFact, Climate-FEVER, TruthfulQA)
- **Model Engine**: Groq LPU (`qwen/qwen3.8-27b`, temp = 0.2)
- **Retrieval Engine**: Multi-Source Concurrent Async Engine (`httpx`, Wikipedia extracts, DuckDuckGo HTML/Lite)
- **Evidence State**: 100% Frozen Disk Cache (`tests/data/frozen_evidence_1000.json`, zero search drift)

---

## 1. Primary Benchmark Results

| System / Configuration | Accuracy | 95% Wilson Score CI | Coverage | Selective Accuracy | False Positives | p50 Latency | ECE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **83.7%** | **[78.1% – 88.1%]** | **78.5%** | **91.5%** | **0 (0.0%)** | **12.16s** | **0.0600** |
| Baseline: Raw Search + LLM | 78.5% | [72.4% – 83.5%] | 73.7% | 89.6% | 0 (0.0%) | 12.06s | 0.0725 |
| Baseline: Ungrounded Zero-Shot | 54.5% | [47.8% – 61.2%] | 38.8% | 96.3% | 0 (0.0%) | 12.26s | 0.1584 |

---

## 2. Paired Statistical Significance Tests (McNemar with Continuity Correction)

### FactGuard AI vs. Ungrounded Zero-Shot LLM
* **Contingency Matrix**:
  - Both Correct: `95`
  - FactGuard Only Won: `80`
  - Ungrounded Only Won: `19`
  - Both Wrong: `15`
* **Discordant Pairs**: `99`
* **Chi-Square Statistic ($\chi^2$)**: `36.3636`
* **p-value**: `p = 0.0`
* **Statistical Significance**: **Statistically Significant at p < 0.01**

### FactGuard AI vs. Raw Web Search Baseline
* **Contingency Matrix**:
  - Both Correct: `155`
  - FactGuard Only Won: `20`
  - Raw Search Only Won: `9`
  - Both Wrong: `25`
* **Discordant Pairs**: `29`
* **Chi-Square Statistic ($\chi^2$)**: `3.4483`
* **p-value**: `p = 0.063318`
* **Statistical Significance**: **Trending at p = 0.063318**

---

## 3. Calibration & Safety Guarantees

* **Expected Calibration Error (ECE)**: `0.0600`.
* **Safety**: Zero false positive inversions (0 of 209 claims). FactGuard prioritizes epistemic abstention over unverified assertions.
