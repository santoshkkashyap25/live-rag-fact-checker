# FactGuard AI: 100-Claim Statistically Powered Benchmark Report
**Timestamp**: 2026-11-15 08:24:26 UTC  
**Evaluation Protocol**: Frozen Evidence Benchmark on 100 Balanced Claims ($N = 100$)  
**Dataset Architecture**: 40 True, 40 False, 20 Unverifiable across 10 academic domains  
**Evaluated Model**: Groq LPU `openai/gpt-oss-120b` (temperature = 0.2, max_tokens = 1536, single deterministic run)  
**Retrieval Engine**: Multi-Engine Async Web Search (DuckDuckGo + Wikipedia + Instant Answers, frozen cache)  

---

## 1. Executive Summary & Comparative Headline Performance ($N = 100$)

| System Configuration | Accuracy | 95% Wilson CI | Coverage | Selective Acc | Macro-F1 | p50 Latency (Frozen) | McNemar Paired Test |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FactGuard AI (Full Pipeline)** | **86.0% (86/100)** | [77.9%, 91.5%] | **70.0%** | **97.1%** | **0.844** | 7.28s | — |
| Raw Web Search + LLM Baseline | 79.0% (79/100) | [70.0%, 85.8%] | 65.0% | 93.8% | 0.777 | 6.75s | $\chi^2 = 3.2727, p = 0.07044$ |
| Ungrounded Zero-Shot LLM | 47.0% (47/100) | [37.5%, 56.7%] | 28.0% | 96.4% | 0.463 | 12.21s | $\chi^2 = 30.7234, p = 0.0$ |

---

## 2. Statistical Significance Analysis (McNemar's Paired Test)

With $N = 100$ claims and substantial discordant pairs, McNemar's test measures whether FactGuard AI's accuracy advantage is statistically significant:

- **FactGuard AI vs. Raw Web Search + LLM**:
  - Contingency: Both Correct = 77, FG Only = 9, Raw Only = 2, Both Wrong/Abstained = 12
  - Discordant Claims ($b + c$): 11
  - $\chi^2 = 3.2727$, **$p$-value = 0.07044** (Statistically significant at $\alpha = 0.05$: False)

- **FactGuard AI vs. Zero-Shot Ungrounded LLM**:
  - Contingency: Both Correct = 43, FG Only = 43, LLM Only = 4, Both Wrong/Abstained = 10
  - Discordant Claims ($b + c$): 47
  - $\chi^2 = 30.7234$, **$p$-value = 0.0** (Statistically significant at $\alpha = 0.01$: True)

---

## 3. Confusion Matrix Breakdown (FactGuard Full, $N = 100$)

```
                           PREDICTED VERDICT
                   True         False      Unverifiable    Total
EXPECTED  True       36           0            4            40
VERDICT   False      0            32           8            40
          Unverif.   0            2            18           20
          Total      36           34           30           100
```

- **False Positives (False claim marked True)**: 0 (0.0%)
- **False Negatives (True claim marked False)**: 0 (0.0%)
- **Unverifiable Abstentions**: 30

---

## 4. Confidence Calibration ($N = 100$, ECE = 0.0402)

| Confidence Bin | Claim Count | Mean Predicted Confidence | Empirical Accuracy | Calibration Gap |
| :--- | :--- | :--- | :--- | :--- |
| 0.00 - 0.50 | 10 | 32.4% | 50.0% | 17.6% |
| 0.50 - 0.70 | 10 | 61.4% | 60.0% | 1.4% |
| 0.70 - 0.85 | 7 | 75.3% | 57.1% | 18.1% |
| 0.85 - 0.95 | 4 | 90.5% | 75.0% | 15.5% |
| 0.95 - 1.00 | 69 | 98.2% | 98.6% | 0.3% |

---

## 5. Domain Breakdown (10 Academic Domains, 10 Claims Each)

Each domain was evaluated with 4 True, 4 False, and 2 Unverifiable claims:
1. **Astrophysics & Space**: Orbital mechanics, cosmic expansion, solar physics, common misconceptions.
2. **Neuroscience & Psychology**: Brain capacity myths, memory consolidation, neuroplasticity.
3. **Molecular Biology & Genetics**: CRISPR, DNA replication, GMO misconceptions, mitochondrial genetics.
4. **Chemistry & Materials Science**: Physical state changes, diamond formation myths, graphene, thermodynamic equilibria.
5. **Human Anatomy & Medicine**: Cardiovascular anatomy, antibiotics vs viral colds, vaccine science, knuckle cracking.
6. **Earth Science & Meteorology**: Stratospheric ozone, tectonic subduction, Coriolis myths, lightning frequency.
7. **World History & Archaeology**: Moon landings, Titanic sinking, Napoleon height myth, medieval torture myths.
8. **Computer Science & Tech**: Cryptography, TCP/IP, Turing tests, 5G viral transmission conspiracies.
9. **Zoology & Animal Behavior**: Dichromatic bovine vision, honeybee sterile foraging, echolocation myths.
10. **Geography & Geopolitics**: Federal capitals, sovereign landmasses, desert definitions.

---

## 6. Verifiable Benchmark Artifacts

- **Benchmark Dataset (100 claims)**: [`tests/data/claims_test_100.json`](tests/data/claims_test_100.json)
- **Frozen Evidence Cache**: [`tests/data/frozen_evidence_100.json`](tests/data/frozen_evidence_100.json)
- **Raw Telemetry**: [`tests/data/eval_results_100.json`](tests/data/eval_results_100.json)
- **Benchmark Runner**: [`tests/run_evaluation_100.py`](tests/run_evaluation_100.py)
