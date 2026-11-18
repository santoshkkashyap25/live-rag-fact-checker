# FactGuard AI: Held-Out Pilot Scientific Evaluation Report (N = 32)

> **Evaluation Standard**: Strictly held-out, decontaminated evaluation suite ($N = 32$). All claims were decontaminated against the 564 development claims using Levenshtein distance filtering ($< 0.65$). Evaluated with **frozen multi-engine web evidence** across all systems to ensure zero retrieval drift.

---

## 1. Headline Empirical Comparison

| System Configuration | 4-Class Accuracy | 95% Wilson CI | FEVER 3-Class Accuracy | Coverage (Decisive) | Selective Precision |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **68.8% (22/32)** | [51.4%, 82.0%] | **84.4%** | **65.6%** (21/32) | **81.0%** |
| Raw Web Search + LLM Baseline | 65.6% (21/32) | [48.3%, 79.6%] | 81.2% | 56.2% (18/32) | 83.3% |
| Fair Ungrounded Zero-Shot LLM | 84.4% (27/32) | [68.2%, 93.1%] | 87.5% | 62.5% (20/32) | 85.0% |

---

## 2. Statistical Significance (Paired Tests)

* **FactGuard AI vs. Raw Web Search Baseline**:
  - Both Correct: `20`
  - Both Wrong: `9`
  - FactGuard Only: `2`
  - Raw Search Only: `1`
  - Discordant Pairs: `3`
  - McNemar Statistic ($\chi^2$): `0.000`
  - Exact Binomial p-value: **p = 1.0000**

* **FactGuard AI vs. Fair Ungrounded Zero-Shot Baseline**:
  - Both Correct: `22`
  - Both Wrong: `5`
  - FactGuard Only: `0`
  - Zero-Shot Only: `5`
  - Discordant Pairs: `5`
  - McNemar Statistic ($\chi^2$): `3.200`
  - Exact Binomial p-value: **p = 0.0625**

---

## 3. 4x4 Confusion Matrices

### FactGuard AI (Full Pipeline)
| Ground Truth \ Predicted | True | False | Unsupported | Unverifiable | Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True** | **8** | 0 | 1 | 0 | 9 |
| **False** | 0 | **9** | 0 | 0 | 9 |
| **Unsupported** | 0 | 2 | **5** | 0 | 7 |
| **Unverifiable** | 0 | 2 | 5 | **0** | 7 |

### Raw Web Search Baseline
| Ground Truth \ Predicted | True | False | Unsupported | Unverifiable | Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True** | **8** | 0 | 1 | 0 | 9 |
| **False** | 0 | **7** | 2 | 0 | 9 |
| **Unsupported** | 0 | 2 | **5** | 0 | 7 |
| **Unverifiable** | 1 | 0 | 5 | **1** | 7 |

### Fair Ungrounded Zero-Shot Baseline
| Ground Truth \ Predicted | True | False | Unsupported | Unverifiable | Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True** | **8** | 0 | 1 | 0 | 9 |
| **False** | 0 | **9** | 0 | 0 | 9 |
| **Unsupported** | 0 | 2 | **5** | 0 | 7 |
| **Unverifiable** | 0 | 1 | 1 | **5** | 7 |

---

## 4. Per-Claim Evaluation Auditing

| ID | Domain | Expected | FactGuard | Raw Search | Zero-Shot | Claim Excerpt |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `HOLDOUT-001` | Cell Biology | `True` | ✅ True | ✅ True | ✅ True | Telomerase reverse transcriptase synthesizes repetitive nucl... |
| `HOLDOUT-002` | Cosmology | `True` | ✅ True | ✅ True | ✅ True | Type Ia supernovae serve as standard candles for measuring c... |
| `HOLDOUT-003` | Immunology | `True` | ✅ True | ✅ True | ✅ True | Mature B lymphocytes undergo somatic hypermutation within ge... |
| `HOLDOUT-004` | Geophysics | `True` | ✅ True | ✅ True | ✅ True | The Mohorovicic discontinuity marks the boundary between Ear... |
| `HOLDOUT-005` | Biochemistry | `True` | ✅ True | ✅ True | ✅ True | The citric acid cycle takes place within the mitochondrial m... |
| `HOLDOUT-006` | Genetics | `True` | ✅ True | ✅ True | ✅ True | X-chromosome inactivation in female placental mammals is med... |
| `HOLDOUT-007` | Meteorology | `True` | ✅ True | ✅ True | ✅ True | The Coriolis effect deflects moving air masses to the right ... |
| `HOLDOUT-008` | Temporal Post-Cu | `True` | ✅ True | ✅ True | ✅ True | NASA's Europa Clipper spacecraft was successfully launched a... |
| `HOLDOUT-009` | Temporal Post-Cu | `True` | ❌ Unsupported | ❌ Unsupported | ❌ Unsupported | The 2024 Nobel Prize in Chemistry was awarded to David Baker... |
| `HOLDOUT-010` | Human Physiology | `False` | ✅ False | ✅ False | ✅ False | Human hair and fingernails continue biological cellular grow... |
| `HOLDOUT-011` | Nutrition | `False` | ✅ False | ❌ Unsupported | ✅ False | Consuming acidic citrus fruits directly lowers physiological... |
| `HOLDOUT-012` | Neuroscience | `False` | ✅ False | ✅ False | ✅ False | Brain scans prove that distinct left-brained individuals are... |
| `HOLDOUT-013` | Virology | `False` | ✅ False | ✅ False | ✅ False | Human immunodeficiency virus particles reproduce by assembli... |
| `HOLDOUT-014` | Astronomy | `False` | ✅ False | ✅ False | ✅ False | The dark craters of the planet Mercury maintain permanent li... |
| `HOLDOUT-015` | Pharmacology | `False` | ✅ False | ✅ False | ✅ False | Penicillin antibiotics treat acute bacterial infections by d... |
| `HOLDOUT-016` | Genetics | `False` | ✅ False | ✅ False | ✅ False | Mature human platelets contain forty-six diploid chromosomes... |
| `HOLDOUT-017` | Temporal Post-Cu | `False` | ✅ False | ✅ False | ✅ False | Boeing's Starliner Calypso crew capsule permanently evacuate... |
| `HOLDOUT-018` | Temporal Post-Cu | `False` | ✅ False | ❌ Unsupported | ✅ False | The 2024 Nobel Prize in Physics was awarded for the experime... |
| `HOLDOUT-019` | Astrobiology | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ✅ Unsupported | Atmospheric biosignature disequilibrium on exoplanet K2-18b ... |
| `HOLDOUT-020` | Particle Physics | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ✅ Unsupported | Sterile right-handed neutrinos with masses near 7 keV accoun... |
| `HOLDOUT-021` | Geobiology | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ✅ Unsupported | Microbial life originated at terrestrial subaerial hot sprin... |
| `HOLDOUT-022` | Neurobiology | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ✅ Unsupported | Quantum entanglement across nuclear spins in intracellular p... |
| `HOLDOUT-023` | Archaeology | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ✅ Unsupported | Submerged Paleolithic megalithic structures in the Persian G... |
| `HOLDOUT-024` | Temporal Post-Cu | `Unsupported` | ❌ False | ❌ False | ❌ False | SpaceX Starship completed its first commercial orbital satel... |
| `HOLDOUT-025` | Temporal Post-Cu | `Unsupported` | ❌ False | ❌ False | ❌ False | An oral small-molecule GLP-1 receptor agonist received final... |
| `HOLDOUT-026` | Philosophy of Mi | `Unverifiable` | ❌ False | ❌ True | ✅ Unverifiable | The subjective qualitative experience of seeing the color re... |
| `HOLDOUT-027` | Aesthetics | `Unverifiable` | ❌ Unsupported | ❌ Unsupported | ✅ Unverifiable | Acoustic orchestral symphony performance provides deeper aes... |
| `HOLDOUT-028` | Ethics & Law | `Unverifiable` | ❌ Unsupported | ✅ Unverifiable | ✅ Unverifiable | Autonomous lethal weapons systems are fundamentally morally ... |
| `HOLDOUT-029` | Cosmology | `Unverifiable` | ❌ False | ❌ Unsupported | ❌ Unsupported | The total information entropy of our observable universe wil... |
| `HOLDOUT-030` | Future Ecology | `Unverifiable` | ❌ Unsupported | ❌ Unsupported | ✅ Unverifiable | Global artificial atmospheric aerosol injection will be perm... |
| `HOLDOUT-031` | Sociology | `Unverifiable` | ❌ Unsupported | ❌ Unsupported | ❌ False | Democratic governance is universally the most productive pol... |
| `HOLDOUT-032` | Personal Prefere | `Unverifiable` | ❌ Unsupported | ❌ Unsupported | ✅ Unverifiable | Handwritten correspondence conveys greater authentic persona... |
