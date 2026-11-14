# FactGuard AI: Evaluation Report
**Timestamp**: 2026-11-14 20:15:38 UTC  
**Evaluation Protocol**: Frozen Evidence Benchmark with Dual Dev / Test Partitioning  
**Evaluated Model**: Groq LPU `openai/gpt-oss-120b` (temperature = 0.2, max_tokens = 1536, single deterministic run)  
**Sample Sizes**: Development Probe ($N=16$), Held-Out Test Set ($N=20$)  
**Evidence Source**: DuckDuckGo HTML + Wikipedia APIs (Frozen on disk to eliminate live search drift)

---

## 1. Executive Summary & Comparative Results (Test Set, $N=20$)

> [!NOTE]
> **Sample Size & Statistical Power Caveat**:
> On an evaluation set of $N=20$ claims, all three systems cannot be statistically distinguished: the 95% Wilson intervals overlap across all configurations, and McNemar's paired tests show no statistically significant difference ($p = 1.000$ vs Raw DDG; $p = 0.371$ vs Ungrounded LLM). For scale, detecting a true 15-percentage-point paired difference with 80% statistical power would require approximately $N \ge 70$ discordant evaluations.

### Headline Comparison (Held-Out Test Set)

| System Configuration | Accuracy | 95% Wilson CI | Coverage | Selective Acc | Macro-F1 | p50 Latency (Frozen) | McNemar $p$-val |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FactGuard AI (Full Pipeline)** | **80.0% (16/20)** | [58.4%, 91.9%] | 70.0% (14/20) | 92.9% (13/14) | 0.778 | 6.28s | — |
| Raw DDG Search + LLM Baseline | 75.0% (15/20) | [53.1%, 88.8%] | 75.0% (15/20) | 86.7% (13/15) | 0.709 | 4.40s | $p = 1.000$ |
| Ungrounded Zero-Shot LLM | 65.0% (13/20) | [43.3%, 81.9%] | 45.0% (9/20) | **100.0% (9/9)** | 0.645 | 2.69s | $p = 0.371$ |

### Critical Observations:
1. **Selective Accuracy vs. Coverage Trade-off**:
   - The ungrounded zero-shot LLM achieved **100.0% selective accuracy** (9 out of 9 answered claims correct), but abstained on over half the dataset (coverage of only 45.0%).
   - FactGuard AI expanded coverage to **70.0%** (14/20 claims answered) while maintaining **92.9% selective accuracy** (13/14 correct).
2. **Error Breakdown & The Single Assertive Failure**:
   - **False Positives**: 0 of 8 false claims judged True (0.0% FP, with 2 abstained).
   - **False Negatives**: 0 of 8 true claims judged False (0.0% FN, with 1 abstained).
   - **Assertive Misclassification**: 1 of 4 unverifiable claims judged False (`TEST-16`, *"Extraterrestrial life forms currently inhabit an underground base on Europa"*). FactGuard asserted `False` with 0.99 confidence because astrobiological consensus documents confirm no evidence of alien life or structures has ever been detected on Europa. In FEVER, speculative claims are labeled Unverifiable/NEI, making this an epistemic consensus mismatch rather than an ungrounded hallucination.
   - **Abstentions (Fail-Safe Defaults)**: 3 claims (`TEST-02`, `TEST-03`, `TEST-04`) were abstained as `Unverifiable` because live search network read timeouts returned 0 snippets during the frozen cache creation pass. The system defaulted to a fail-safe abstention rather than hallucinating without evidence.

---

## 2. Component Ablation Study & Per-Claim Outcome Matrix

### Ablation Summary ($N=20$)

| Configuration | What was Removed | Accuracy | Coverage | Selective Acc | Macro-F1 | Observable Finding |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FactGuard Full** | *None (Reference)* | **80.0%** | **70.0%** | **92.9%** | **0.778** | Baseline full pipeline. |
| `ablation_no_spacy` | SpaCy Extraction | 80.0% | 70.0% | 92.9% | 0.778 | **0 delta on clean benchmark prose.** (Extraction is critical for noisy conversational prompts, but redundant on isolated factual sentences). |
| `ablation_no_domain_trust` | Domain Authority Weights | 75.0% | 75.0% | 86.7% | 0.709 | **Driven by 1 claim** (`TEST-20`). Without institutional weighting, speculation on Antarctic ice shifted to `False`. |
| `ablation_no_rerank` | BM25Okapi Re-ranking | 75.0% | 75.0% | 86.7% | 0.709 | **Driven by 1 claim** (`TEST-20`). Default search snippet order matches raw search. |
| `ablation_ddg_only` | Wikipedia Integration | 75.0% | 75.0% | 86.7% | 0.709 | **Driven by 1 claim** (`TEST-20`). |
| `ablation_wikipedia_only` | Open Web Retrieval (DDG) | 60.0% | 60.0% | 83.3% | 0.576 | **Substantial 4-claim drop** (`TEST-15`, `TEST-17`, `TEST-19`, `TEST-20` abstained). Proves Wikipedia alone lacks sufficient coverage for modern misconceptions. |

> [!IMPORTANT]
> **Methodological Note on 1-Claim Deltas**:  
> In a 20-claim dataset, each 5.0% shift corresponds to exactly **one claim**. Four configurations (`baseline_raw_ddg`, `no_domain_trust`, `no_rerank`, and `ddg_only`) produced identical summary statistics. As the matrix below reveals, a single claim (`TEST-20`) accounts for all four deltas. Thus, domain trust and BM25 re-ranking cannot be statistically separated from raw search on this sample size.

### Per-Claim Outcome Matrix

| Claim ID | Exp | `factguard_full` | `raw_ddg` | `ungrounded` | `no_spacy` | `no_domain_trust` | `no_rerank` | `wikipedia_only` | `ddg_only` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TEST-01` | `True` | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True |
| `TEST-02` | `True` | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS |
| `TEST-03` | `Fals` | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS |
| `TEST-04` | `Fals` | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS | ⏸️ ABS |
| `TEST-05` | `True` | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True |
| `TEST-06` | `True` | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True |
| `TEST-07` | `Fals` | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals |
| `TEST-08` | `Fals` | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals |
| `TEST-09` | `Unve` | ✅ Unve | ✅ Unve | ✅ Unve | ✅ Unve | ✅ Unve | ✅ Unve | ✅ Unve | ✅ Unve |
| `TEST-10` | `Unve` | ✅ Unve | ✅ Unve | ✅ Unve | ✅ Unve | ✅ Unve | ✅ Unve | ✅ Unve | ✅ Unve |
| `TEST-11` | `True` | ✅ True | ✅ True | ⏸️ ABS | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True |
| `TEST-12` | `Fals` | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals | ✅ Fals |
| `TEST-13` | `True` | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True |
| `TEST-14` | `True` | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True |
| `TEST-15` | `Fals` | ✅ Fals | ✅ Fals | ⏸️ ABS | ✅ Fals | ✅ Fals | ✅ Fals | ⏸️ ABS | ✅ Fals |
| `TEST-16` | `Unve` | ❌ Fals | ❌ Fals | ✅ Unve | ❌ Fals | ❌ Fals | ❌ Fals | ❌ Fals | ❌ Fals |
| `TEST-17` | `Fals` | ✅ Fals | ✅ Fals | ⏸️ ABS | ✅ Fals | ✅ Fals | ✅ Fals | ⏸️ ABS | ✅ Fals |
| `TEST-18` | `True` | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True | ✅ True |
| `TEST-19` | `Fals` | ✅ Fals | ✅ Fals | ⏸️ ABS | ✅ Fals | ✅ Fals | ✅ Fals | ⏸️ ABS | ✅ Fals |
| `TEST-20` | `Unve` | ✅ Unve | ❌ Fals | ✅ Unve | ✅ Unve | ❌ Fals | ❌ Fals | ❌ Fals | ❌ Fals |

*Legend: `✅` = Correct judgment; `⏸️ ABS` = Abstained (`Unverifiable`); `❌` = Misclassified.*

---

## 3. Full $3 \times 3$ Confusion Matrix (FactGuard Full, $N=20$)

```
                           PREDICTED VERDICT
                   True         False      Unverifiable    Total
EXPECTED  True       7            0             1            8
VERDICT   False      0            6             2            8
          Unverif.   0            1             3            4
          Total      7            7             6           20
```

- **Accuracy**: $16 / 20 = 80.0\%$ (Wilson 95% CI: `[58.4%, 91.9%]`)
- **Coverage**: $14 / 20 = 70.0\%$
- **Selective Accuracy**: $13 / 14 = 92.9\%$ (Wilson 95% CI: `[68.5%, 98.7%]`)
- **Macro-F1**: $0.778$

---

## 4. Confidence Score Semantics & Calibration Illustration

### Confidence Score Definitions
- **Assertive Decisions (`True` or `False`)**: Confidence reflects the model's posterior certainty given the retrieved evidence corroboration or refutation.
- **Abstentions (`Unverifiable`)**:
  - A score of **`0.00` to `0.20`** signifies a **fail-safe default**: retrieval failed, returned zero snippets, or snippets were completely irrelevant.
  - A score of **`0.85` to `0.99`** signifies **epistemic certainty of unverifiability**: the claim is demonstrably an unfalsifiable subjective opinion or an unprovable future prediction.

> [!WARNING]
> With $N=20$ claims and 15 items clustering in the $[0.95, 1.00]$ bin, the calculated Expected Calibration Error (ECE = 0.075) is an exploratory sample metric rather than a generalized statistical calibration proof. 

| Confidence Bin | Count | Mean Predicted Confidence | Empirical Accuracy | Calibration Gap | Finding |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **0.00 – 0.50** | 3 | 13.3% | 0.0% | 13.3% | Fail-safe retrieval timeouts default to low-confidence abstention. |
| **0.50 – 0.70** | 0 | — | — | — | — |
| **0.70 – 0.85** | 0 | — | — | — | — |
| **0.85 – 0.95** | 2 | 85.0% | 100.0% | 15.0% | Conservative confidence scores on standard true propositions. |
| **0.95 – 1.00** | 15 | 98.7% | 93.3% | 5.3% | 14 of 15 claims correct. The single failure in this bin was `TEST-16` (alien base on Europa judged False with 0.99 confidence). |

---

## 5. Statistical Significance (McNemar's Paired Test)

- **FactGuard AI vs. Raw DDG Search + LLM**:
  - Contingency: Both Correct = 15, FG Only = 1 (`TEST-20`), Raw Only = 0, Both Wrong/Abstained = 4
  - $\chi^2 = 0.000$, $p = 1.000$ (Non-significant on $N=20$)
- **FactGuard AI vs. Zero-Shot Ungrounded LLM**:
  - Contingency: Both Correct = 12, FG Only = 4 (`TEST-11`, `TEST-15`, `TEST-17`, `TEST-19`), LLM Only = 1 (`TEST-16`), Both Wrong/Abstained = 3
  - $\chi^2 = 0.800$, $p = 0.371$ (Non-significant on $N=20$)

---

## 6. Construction of the Test & Dev Sets

### Test Set Construction ($N=20$)
The 20 test claims were sampled across physical sciences, biology, history, and misconceptions:
- **8 True Propositions**: Sourced from FEVER and verified scientific ground truth.
- **8 False Propositions**: Sourced from TruthfulQA documented misconceptions.
- **4 Unverifiable Propositions**:
  - `TEST-09`: Speculative future event (reincarnation of Alexander the Great in 2085).
  - `TEST-10`: Subjective aesthetic opinion (vanilla is objectively the greatest flavor).
  - `TEST-16`: Unproven astrobiological speculation (alien base on Europa). Note the label ambiguity: in FEVER, speculative claims are labeled Not Enough Info (NEI), but scientific surveys confirming the absence of artificial structures led the model to judge it False.
  - `TEST-20`: Speculative future discovery (secret Neanderthal colony in Antarctica in 2040).

### Development Set Audit & Root-Cause Error Analysis ($N=16$)
The 16 baseline claims ([`claims_dev.json`](tests/data/claims_dev.json)) served as an initial development probe. Historical evaluation showed 13/16 accuracy (81.2%). Rather than "epistemic humility," inspecting logs shows specific infrastructure and prompt causes for the 3 historical abstentions:

| Dev ID | Claim | Expected | Got | Conf | Diagnostic Root Cause |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `DEV-06` | Liquid water contracts when freezing into ice | `False` | `Unverifiable` | 0.20 | **Prompt Literal-Negation Rigidity**: Snippet stated water *expands* when freezing; prompt instructions required literal refutation, so the model abstained rather than inferring that expansion negates contraction. |
| `DEV-09` | Bulls charge specifically because they see red | `False` | `Unverifiable` | 0.00 | **Retrieval Snippet Truncation**: A 10-second timeout truncated search snippets before the explanation of bovine dichromacy (red-blindness) was captured. |
| `DEV-12` | Napoleon Bonaparte was unusually short | `False` | `Unverifiable` | 0.80 | **Unit Discrepancy Guard**: Conflicting historical documentation comparing French inches (*pouces*, 5'2") vs Imperial inches (5'6") triggered the numerical variance dispute guard. |

---

## 7. Methodological Scope & Known Limitations

1. **Pre-training Contamination**: TruthfulQA questions and common misconceptions are extensively represented in modern LLM pre-training corpora, which inflates ungrounded baseline recall.
2. **Retrieval Network Flakiness**: During frozen cache building, 3 of 20 test queries (15%) suffered HTTP read timeouts, forcing zero-snippet payloads that defaulted to `Unverifiable`.
3. **Latency Profile**: End-to-end median verification latency on the live server averages **6.28s** on frozen evidence and **~22s** when executing live DuckDuckGo + Wikipedia network requests.

---

## 8. Verifiable Benchmark Files in Repository

- **Evaluation Script**: [`tests/run_evaluation.py`](tests/run_evaluation.py)
- **Dev Set Probe (16 claims)**: [`tests/data/claims_dev.json`](tests/data/claims_dev.json)
- **Held-Out Test Set (20 claims)**: [`tests/data/claims_test.json`](tests/data/claims_test.json)
- **Frozen Evidence Cache**: [`tests/data/frozen_evidence.json`](tests/data/frozen_evidence.json)
- **Raw Evaluation Telemetry**: [`tests/data/eval_results.json`](tests/data/eval_results.json)
- **Benchmark Conversion Rules**: [`tests/data/conversion_rules.md`](tests/data/conversion_rules.md)
- **Adversarial Regression Suite**: [`tests/red_team_suite.py`](tests/red_team_suite.py)
