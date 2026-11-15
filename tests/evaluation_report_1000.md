# FactGuard AI: Academic Gold-Standard Benchmark Report (N = 105)

**Evaluation Environment**:
- **Dataset**: `tests/data/claims_test_1000.json` (105 balanced claims across 25 scientific & empirical domains)
- **Class Proportions**: 40.0% True, 40.0% False, 20.0% Unverifiable (FEVER, SciFact, Climate-FEVER, TruthfulQA)
- **Model Engine**: Groq LPU (`openai/gpt-oss-20b`, temp = 0.2)
- **Retrieval Engine**: Multi-Source Concurrent Async Engine (`httpx`, Wikipedia extracts, DuckDuckGo HTML/Lite)
- **Evidence State**: 100% Frozen Disk Cache (`tests/data/frozen_evidence_1000.json`, zero search drift)

---

## 1. Primary Benchmark Results

| System / Configuration | Accuracy | 95% Wilson Score CI | Coverage | Selective Accuracy | False Positives | p50 Latency | ECE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **86.7%** | **[78.9% – 91.9%]** | **71.4%** | **97.3%** | **0 (0.0%)** | **7.60s** | **0.0397** |
| Baseline: Raw Search + LLM | 79.0% | [70.3% – 85.7%] | 65.7% | 94.2% | 0 (0.0%) | 6.98s | 0.0302 |
| Baseline: Ungrounded Zero-Shot | 46.7% | [37.4% – 56.2%] | 28.6% | 96.7% | 0 (0.0%) | 12.19s | 0.2370 |

---

## 2. Paired Statistical Significance Tests (McNemar with Continuity Correction)

### FactGuard AI vs. Ungrounded Zero-Shot LLM
* **Contingency Matrix**:
  - Both Correct: `45`
  - FactGuard Only Won: `46`
  - Ungrounded Only Won: `4`
  - Both Wrong: `10`
* **Discordant Pairs**: `50`
* **Chi-Square Statistic ($\chi^2$)**: `33.62`
* **p-value**: `p = 0.0`
* **Statistical Significance**: **Statistically Significant at p < 0.01**

### FactGuard AI vs. Raw Web Search Baseline
* **Contingency Matrix**:
  - Both Correct: `81`
  - FactGuard Only Won: `10`
  - Raw Search Only Won: `2`
  - Both Wrong: `12`
* **Discordant Pairs**: `12`
* **Chi-Square Statistic ($\chi^2$)**: `4.0833`
* **p-value**: `p = 0.043308`
* **Statistical Significance**: **Trending at p = 0.043308**

---

## 3. Calibration & Safety Guarantees

* **Expected Calibration Error (ECE)**: `0.0397`.
* **Safety**: Zero false positive inversions (0 of 105 claims). FactGuard prioritizes epistemic abstention over unverified assertions.
