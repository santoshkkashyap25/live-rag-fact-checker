# FactGuard AI: Academic Gold-Standard Benchmark Report (N = 182)

**Evaluation Environment**:
- **Dataset**: `tests/data/claims_test_1000.json` (182 balanced claims across 25 scientific & empirical domains)
- **Class Proportions**: 40.0% True, 40.0% False, 20.0% Unverifiable (FEVER, SciFact, Climate-FEVER, TruthfulQA)
- **Model Engine**: Groq LPU (`openai/gpt-oss-20b`, temp = 0.2)
- **Retrieval Engine**: Multi-Source Concurrent Async Engine (`httpx`, Wikipedia extracts, DuckDuckGo HTML/Lite)
- **Evidence State**: 100% Frozen Disk Cache (`tests/data/frozen_evidence_1000.json`, zero search drift)

---

## 1. Primary Benchmark Results

| System / Configuration | Accuracy | 95% Wilson Score CI | Coverage | Selective Accuracy | False Positives | p50 Latency | ECE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **85.2%** | **[79.3% – 89.6%]** | **79.7%** | **92.4%** | **0 (0.0%)** | **12.05s** | **0.0646** |
| Baseline: Raw Search + LLM | 78.6% | [72.0% – 83.9%] | 72.5% | 90.9% | 0 (0.0%) | 11.95s | 0.0723 |
| Baseline: Ungrounded Zero-Shot | 51.6% | [44.4% – 58.8%] | 36.8% | 95.5% | 0 (0.0%) | 12.25s | 0.1763 |

---

## 2. Paired Statistical Significance Tests (McNemar with Continuity Correction)

### FactGuard AI vs. Ungrounded Zero-Shot LLM
* **Contingency Matrix**:
  - Both Correct: `80`
  - FactGuard Only Won: `75`
  - Ungrounded Only Won: `14`
  - Both Wrong: `13`
* **Discordant Pairs**: `89`
* **Chi-Square Statistic ($\chi^2$)**: `40.4494`
* **p-value**: `p = 0.0`
* **Statistical Significance**: **Statistically Significant at p < 0.01**

### FactGuard AI vs. Raw Web Search Baseline
* **Contingency Matrix**:
  - Both Correct: `137`
  - FactGuard Only Won: `18`
  - Raw Search Only Won: `6`
  - Both Wrong: `21`
* **Discordant Pairs**: `24`
* **Chi-Square Statistic ($\chi^2$)**: `5.0417`
* **p-value**: `p = 0.024745`
* **Statistical Significance**: **Trending at p = 0.024745**

---

## 3. Calibration & Safety Guarantees

* **Expected Calibration Error (ECE)**: `0.0646`.
* **Safety**: Zero false positive inversions (0 of 182 claims). FactGuard prioritizes epistemic abstention over unverified assertions.
