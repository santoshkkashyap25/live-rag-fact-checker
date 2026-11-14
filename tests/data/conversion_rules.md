# Benchmark Claim Conversion Rules & Dataset Specification

This document formalizes the mapping of public academic benchmarks (TruthfulQA and FEVER) into the FactGuard AI 3-way evaluation framework (`True`, `False`, `Unverifiable`).

---

## 1. TruthfulQA (Lin et al., NeurIPS 2022) Conversion Rules

TruthfulQA evaluates whether language models mimic human falsehoods and popular misconceptions across 38 categories (health, law, finance, science, politics).

### Conversion Logic:
1. **True Proposition Mapping**:
   - The question is combined with its documented *Best Answer* into a declarative factual sentence.
   - Example:
     - Question: *"What happens if you crack your knuckles a lot?"*
     - Best Answer: *"Cracking your knuckles causes no harm and does not cause arthritis."*
     - Claim: `Cracking knuckles frequently does not cause arthritis or joint damage.`
     - Label: `True`
2. **False Proposition Mapping**:
   - The question is combined with its documented *Common Misconception* into a declarative claim.
   - Example:
     - Claim: `Cracking knuckles frequently causes arthritis and permanent joint enlargement.`
     - Label: `False`

### Label Contamination & Leakage Safeguard:
- **Web Contamination**: Search engines may index QA benchmarks directly. 
- **Defense**: FactGuard extracts the factual proposition through SpaCy dependency parsing and queries atomic entity-predicate relations (e.g. `knuckle cracking arthritis medical study`), searching for peer-reviewed consensus rather than benchmark QA strings.

---

## 2. FEVER (Fact Extraction and VERification - Thorne et al., NAACL 2018)

FEVER provides 185,445 claims cross-referenced against Wikipedia articles.

### Label Mapping (3-Way):
| FEVER Label | FactGuard Evaluation Label | Definition |
| :--- | :--- | :--- |
| **SUPPORTS** | `True` | Authoritative evidence explicitly confirms the core proposition. |
| **REFUTES** | `False` | Authoritative evidence contradicts or disproves the core proposition. |
| **NOT ENOUGH INFO** | `Unverifiable` | Retrieved evidence provides zero verifiable grounding, or claim is unverifiable subjective speculation. |

### Wikipedia Staleness & Bias Safeguard:
- FEVER ground-truth was constructed against a static June 2017 Wikipedia dump.
- Several real-world claims have undergone temporal drift (e.g., office holders, records, population metrics).
- **Ablation check**: FEVER claims are evaluated both with Wikipedia enabled and with Wikipedia disabled (DuckDuckGo open web only) to isolate structural reliance on Wikipedia.

---

## 3. Dataset Split Protocol (Point 2)

- **Development Set (`claims_dev.json`)**: 
  - 16 baseline claims used for hyperparameter calibration, initial regression tracking, and prompt tuning.
- **Test Set (`claims_test.json`)**: 
  - Strictly held-out, untouched claims evaluated under frozen conditions.
  - Balanced across domains: Physical Sciences, Health & Medicine, History & Culture, Geography & Society, and Misconceptions.
  - Three-class distribution: ~40% True, ~40% False, ~20% Unverifiable.
