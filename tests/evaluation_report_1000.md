# FactGuard AI: Development Evaluation & Failure Mode Audit (564 Unique Claims)

> **Methodological Disclosure**:
> - **Evaluation Status**: **Development Audit (Not Held-Out)**. The 564 unique claims evaluated here include items and themes from earlier development and test iterations.
> - **Dataset Provenance**: The 1,000-row file (`tests/data/claims_test_1000.json`) consists of **564 unique base propositions** (222 True, 223 False, 119 Unverifiable) plus **436 synthetic variant repetitions** across 46 multi-item clusters (appended suffixes like `(Observation #X)`, `(Myth variant #X)`).
> - **Statistical Confound**: Uncorrected McNemar significance testing across all 1,000 rows treats repeated items as independent, artificially deflating $p$-values. When accounting for intra-cluster correlation via cluster bootstrapping, the paired lead over raw search is **not statistically significant at $\alpha = 0.05$** ($p = 0.0654$).
> - **Zero-Shot Baseline Caveat**: The ungrounded zero-shot baseline was prompted with empty evidence under a RAG prompt where Rule 3 explicitly defined absent evidence as `Unverifiable`. The zero-shot abstention rate (44.6%) is largely a prompt artifact.

---

## 1. Primary Evaluation on Deduplicated Unique Claims ($N = 564$)

Evaluating each base proposition exactly once (using its first un-suffixed appearance) removes all duplicate weighting:

| System / Configuration | Overall Accuracy | 95% Wilson Score CI | Coverage (Decisive) | Selective Precision | Confident Errors |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **83.87%** (473/564) | [80.6% – 86.7%] | **75.53%** (426/564) | **91.31%** (389/426) | 37 (6.6%) |
| **Baseline: Raw Search + LLM** | 79.61% (449/564) | [76.1% – 82.7%] | 69.86% (394/564) | 91.12% (359/394) | 35 (6.2%) |
| **Baseline: Ungrounded Zero-Shot** | 63.83% (360/564) | [59.8% – 67.7%] | 52.30% (295/564) | 90.51% (267/295) | 28 (5.0%) |

### Key Observation: Selective Precision is Constant
Selective precision across all three systems on decisive answers is virtually identical (**91.3% vs 91.1% vs 90.5%**). Grounding and retrieval pipeline components do not buy higher precision; they buy **higher decisive coverage** (75.5% vs 69.9% vs 52.3%) at equivalent precision.

---

## 2. Statistical Analysis: Unique Claims vs. Cluster Bootstrap

### A. Paired Comparison on Unique Claims ($N = 564$)
* **Contingency Matrix (FactGuard vs. Raw Search)**:
  * Both Correct: `426`
  * FactGuard Won Alone ($b$): `47`
  * Raw Search Won Alone ($c$): `23`
  * Both Incorrect: `68`
* **Discordant Pairs**: `70`
* **Net Lead**: $+24$ claims in FactGuard's favor
* **Paired Accuracy Difference**: **$+4.26$ percentage points** [95% CI: $+1.37\%$ to $+7.14\%$]
* **McNemar Chi-Square (Edwards Correction)**: $\chi^2 = 7.5571, \mathbf{p = 0.0060}$

### B. Cluster Bootstrap on Full 1,000 Dataset (10,000 Resamples of 564 Clusters)
When intra-cluster correlation of the 46 repeated proposition clusters is preserved:
* **Mean Paired Difference**: **$+3.29$ percentage points**
* **Cluster-Robust 95% Confidence Interval**: **`[-0.11% to +6.86%]`**
* **Cluster Bootstrap $p$-value**: **$p = 0.0654$**
* **Finding**: The confidence interval crosses zero. FactGuard demonstrates a modest positive point estimate (+3.29 pts) over raw web search that this dataset can neither definitively confirm nor rule out.

---

## 3. Structural Asymmetry: Determinable vs. Unverifiable Claims

Breaking down the 564 unique claims by ground truth class reveals two opposing effects:

| Ground Truth Class | Count | FactGuard Recall | Raw Search Recall | Zero-Shot Recall | Net Effect |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **True Claims** | 222 | **87.8%** (195/222) | 81.1% (180/222) | 56.8% (126/222) | FactGuard leads by **+6.7 pts** |
| **False Claims** | 223 | **87.0%** (194/223) | 80.3% (179/223) | 63.2% (141/223) | FactGuard leads by **+6.7 pts** |
| **Unverifiable Claims** | 119 | **70.6%** (84/119) | **75.6%** (90/119) | **78.2%** (93/119) | FactGuard trails by **-5.0 pts** |

* On **determinable claims ($N = 445$)**, FactGuard resolves 87.4% against 80.7% for raw search (+30 net correct).
* On **unverifiable claims ($N = 119$)**, FactGuard performs worse than both baselines due to a tendency to read absence of evidence as refutation.
* Headline accuracy is a weighted sum of these opposing effects, making single-number benchmarks sensitive to the proportion of unverifiable claims chosen by the author.

---

## 4. Full 3×3 Confusion Matrices ($N = 564$)

### FactGuard AI (Full Pipeline)
| Ground Truth \ Predicted | True | False | Unverifiable | Total | Recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True** | **195** | 2 | 25 | 222 | 87.8% |
| **False** | 0 | **194** | 29 | 223 | 87.0% |
| **Unverifiable** | 3 | 32 | **84** | 119 | 70.6% |
| **Total Predicted** | 198 | 228 | 138 | 564 | — |

### Baseline: Raw Web Search + LLM
| Ground Truth \ Predicted | True | False | Unverifiable | Total | Recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True** | **180** | 6 | 36 | 222 | 81.1% |
| **False** | 0 | **179** | 44 | 223 | 80.3% |
| **Unverifiable** | 2 | 27 | **90** | 119 | 75.6% |
| **Total Predicted** | 182 | 212 | 170 | 564 | — |

### Baseline: Ungrounded Zero-Shot LLM
| Ground Truth \ Predicted | True | False | Unverifiable | Total | Recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True** | **126** | 2 | 94 | 222 | 56.8% |
| **False** | 0 | **141** | 82 | 223 | 63.2% |
| **Unverifiable** | 1 | 25 | **93** | 119 | 78.2% |
| **Total Predicted** | 127 | 168 | 269 | 564 | — |

---

## 5. Failure Mode Audit: The 32 "Unverifiable $\rightarrow$ False" Cases

Detailed manual inspection of the 32 cases where FactGuard judged an `Unverifiable` claim as `False` categorizes the failure modes:

| Category | Count | % | Diagnosis |
| :--- | :---: | :---: | :--- |
| **Category A: Label Policy / Definite Refutations** | **7** | 21.9% | Synthetic dataset label error. Modern consensus actively refutes the proposition (e.g., *Homo floresiensis* surviving to 1850 CE, Shakespeare authored by Edward de Vere, human evolution has completely ceased). |
| **Category B: Future Speculative Projections** | **11** | 34.4% | Prompt rule conflict. Claims asserted definitive future events ("by 2035", "by 2040"). The model attacked the lack of current proof and judged them `False` despite Rule 3 indicating future events are unverifiable. |
| **Category C: Absence of Evidence Read as Refutation** | **13** | 40.6% | Genuine model overreach. Prompt clauses (`Evidence of Absence` and `Universal Quantifiers`) pushed the model to treat unconfirmed hypotheses (e.g., *life on Europa*, *Type II civilization in Andromeda*, *Planet Nine at 400 AU*) as refuted. |
| **Category D: Retrieval Failure / Hallucinated Citation** | **1** | 3.1% | Retrieval returned irrelevant snippets (Kanye West album lyrics for classical piano focus). The model fabricated a citation ("source 4 notes...") to declare the claim false. |

---

## 6. Prompt Tuning Contamination Post-Mortem

Git history analysis confirms that in commit `ff26ddc`, ad-hoc rules were added to `_create_enhanced_prompt()` specifically referencing prior test failures:
- *"alien base on Europa"* (hardcoded from held-out pilot test claim `TEST-16`).
- *"water expands upon freezing"* and *"bulls rage because they see red"* (hardcoded from dev failures).

**The Engineering Lesson**:
Adding ad-hoc prompt clauses to patch specific test failures introduced systemic overreach: the rule added to fix the Europa claim caused 13 other unproven hypotheses to be falsely classified as refuted. 

**Corrective Action**:
FactGuard has transitioned to a clean **4-class epistemic taxonomy** (`True`, `False`, `Unsupported`, `Unverifiable`), deleted all ad-hoc patch rules, and instituted automated citation faithfulness verification.
