# FactGuard AI: Academic Gold-Standard Benchmark Report (N = 206)

**Evaluation Environment**:
- **Dataset**: `tests/data/claims_test_1000.json` (206 balanced claims across 25 scientific & empirical domains)
- **Class Proportions**: 40.0% True, 40.0% False, 20.0% Unverifiable (FEVER, SciFact, Climate-FEVER, TruthfulQA)
- **Model Engine**: Groq LPU (`qwen/qwen3.8-27b`, temp = 0.2)
- **Retrieval Engine**: Multi-Source Concurrent Async Engine (`httpx`, Wikipedia extracts, DuckDuckGo HTML/Lite)
- **Evidence State**: 100% Frozen Disk Cache (`tests/data/frozen_evidence_1000.json`, zero search drift)

---

## 1. Primary Benchmark Results

| System / Configuration | Accuracy | 95% Wilson Score CI | Coverage | Selective Accuracy | False Positives | p50 Latency | ECE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **84.0%** | **[78.4% – 88.4%]** | **78.6%** | **91.4%** | **0 (0.0%)** | **12.16s** | **0.0629** |
| Baseline: Raw Search + LLM | 78.2% | [72.0% – 83.2%] | 73.3% | 89.4% | 0 (0.0%) | 12.06s | 0.0741 |
| Baseline: Ungrounded Zero-Shot | 53.9% | [47.1% – 60.6%] | 37.9% | 96.2% | 0 (0.0%) | 12.26s | 0.1611 |

---

## 2. Paired Statistical Significance Tests (McNemar with Continuity Correction)

### FactGuard AI vs. Ungrounded Zero-Shot LLM
* **Contingency Matrix**:
  - Both Correct: `93`
  - FactGuard Only Won: `80`
  - Ungrounded Only Won: `18`
  - Both Wrong: `15`
* **Discordant Pairs**: `98`
* **Chi-Square Statistic ($\chi^2$)**: `37.9694`
* **p-value**: `p = 0.0`
* **Statistical Significance**: **Statistically Significant at p < 0.01**

### FactGuard AI vs. Raw Web Search Baseline
* **Contingency Matrix**:
  - Both Correct: `153`
  - FactGuard Only Won: `20`
  - Raw Search Only Won: `8`
  - Both Wrong: `25`
* **Discordant Pairs**: `28`
* **Chi-Square Statistic ($\chi^2$)**: `4.3214`
* **p-value**: `p = 0.037635`
* **Statistical Significance**: **Trending at p = 0.037635**

---

## 3. Calibration & Safety Guarantees

* **Expected Calibration Error (ECE)**: `0.0629`.
* **Safety**: Zero false positive inversions (0 of 206 claims). FactGuard prioritizes epistemic abstention over unverified assertions.
