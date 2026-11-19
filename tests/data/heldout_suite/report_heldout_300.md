# FactGuard AI: Scaled Scientific Evaluation Report (N = 300)

> **Evaluation Standard**: Strictly held-out, decontaminated benchmark suite ($N = 300$). All claims were decontaminated against the 1,016 development claims using Levenshtein distance filtering ($< 0.60$). Evaluated with **frozen multi-engine web evidence** across all systems to eliminate retrieval drift.

---

## 1. Headline Empirical Comparison

| System Configuration | 4-Class Accuracy | 95% Wilson CI | FEVER 3-Class Accuracy | Coverage (Decisive) | Selective Precision |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **60.7% (182/300)** | [55.0%, 66.0%] | **67.3%** | **35.3%** (106/300) | **68.9%** |
| Raw Web Search + LLM Baseline | 56.3% (169/300) | [50.7%, 61.8%] | 64.7% | 27.7% (83/300) | 73.5% |
| Fair Ungrounded Zero-Shot LLM | 72.0% (216/300) | [66.7%, 76.8%] | 76.0% | 58.7% (176/300) | 66.5% |

---

## 2. Statistical Significance (Paired Tests)

* **FactGuard AI vs. Raw Web Search Baseline**:
  - Both Correct: `152`
  - Both Wrong: `101`
  - FactGuard Only ($b$): `30`
  - Raw Search Only ($c$): `17`
  - Discordant Pairs: `47`
  - McNemar Statistic ($\chi^2$): `3.064`
  - Exact Binomial p-value: **p = 0.0789**

* **FactGuard AI vs. Fair Ungrounded Zero-Shot Baseline**:
  - Both Correct: `150`
  - Both Wrong: `52`
  - FactGuard Only ($b$): `32`
  - Zero-Shot Only ($c$): `66`
  - Discordant Pairs: `98`
  - McNemar Statistic ($\chi^2$): `11.112`
  - Exact Binomial p-value: **p = 0.0008**

---

## 3. 4x4 Confusion Matrices

### FactGuard AI (Full Pipeline)
| Ground Truth \ Predicted | True | False | Unsupported | Unverifiable | Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True** | **28** | 11 | 36 | 0 | 75 |
| **False** | 1 | **45** | 29 | 0 | 75 |
| **Unsupported** | 1 | 18 | **53** | 3 | 75 |
| **Unverifiable** | 0 | 2 | 17 | **56** | 75 |

### Raw Web Search Baseline
| Ground Truth \ Predicted | True | False | Unsupported | Unverifiable | Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True** | **21** | 5 | 49 | 0 | 75 |
| **False** | 0 | **40** | 35 | 0 | 75 |
| **Unsupported** | 0 | 16 | **58** | 1 | 75 |
| **Unverifiable** | 1 | 0 | 24 | **50** | 75 |

### Fair Ungrounded Zero-Shot Baseline
| Ground Truth \ Predicted | True | False | Unsupported | Unverifiable | Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True** | **50** | 17 | 7 | 1 | 75 |
| **False** | 3 | **67** | 2 | 3 | 75 |
| **Unsupported** | 10 | 28 | **33** | 4 | 75 |
| **Unverifiable** | 0 | 1 | 8 | **66** | 75 |

---

## 4. Per-Claim Evaluation Auditing (First 100 Claims)

| ID | Domain | Expected | FactGuard | Raw Search | Zero-Shot | Claim Excerpt |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `HOLDOUT-001` | Cell Biology | `True` | ✅ True | ❌ Unsupported | ✅ True | Telomerase reverse transcriptase synthesizes repetitive nucl... |
| `HOLDOUT-002` | Cosmology | `True` | ✅ True | ✅ True | ✅ True | Type Ia supernovae serve as standard candles for measuring c... |
| `HOLDOUT-003` | Immunology | `True` | ✅ True | ✅ True | ✅ True | Mature B lymphocytes undergo somatic hypermutation within ge... |
| `HOLDOUT-004` | Geophysics | `True` | ✅ True | ✅ True | ✅ True | The Mohorovicic discontinuity marks the boundary between Ear... |
| `HOLDOUT-005` | Biochemistry | `True` | ✅ True | ✅ True | ✅ True | The citric acid cycle takes place within the mitochondrial m... |
| `HOLDOUT-006` | Genetics | `True` | ✅ True | ✅ True | ✅ True | X-chromosome inactivation in female placental mammals is med... |
| `HOLDOUT-007` | Meteorology | `True` | ✅ True | ✅ True | ✅ True | The Coriolis effect deflects moving air masses to the right ... |
| `HOLDOUT-008` | Temporal Post-Cu | `True` | ✅ True | ✅ True | ✅ True | NASA's Europa Clipper spacecraft was successfully launched a... |
| `HOLDOUT-009` | Temporal Post-Cu | `True` | ❌ False | ❌ False | ❌ Unverifiable | The 2024 Nobel Prize in Chemistry was awarded to David Baker... |
| `HOLDOUT-010` | Human Physiology | `False` | ✅ False | ❌ Unsupported | ✅ False | Human hair and fingernails continue biological cellular grow... |
| `HOLDOUT-011` | Nutrition | `False` | ✅ False | ❌ Unsupported | ✅ False | Consuming acidic citrus fruits directly lowers physiological... |
| `HOLDOUT-012` | Neuroscience | `False` | ✅ False | ❌ Unsupported | ✅ False | Brain scans prove that distinct left-brained individuals are... |
| `HOLDOUT-013` | Virology | `False` | ✅ False | ✅ False | ✅ False | Human immunodeficiency virus particles reproduce by assembli... |
| `HOLDOUT-014` | Astronomy | `False` | ✅ False | ❌ Unsupported | ✅ False | The dark craters of the planet Mercury maintain permanent li... |
| `HOLDOUT-015` | Pharmacology | `False` | ✅ False | ✅ False | ✅ False | Penicillin antibiotics treat acute bacterial infections by d... |
| `HOLDOUT-016` | Genetics | `False` | ✅ False | ✅ False | ✅ False | Mature human platelets contain forty-six diploid chromosomes... |
| `HOLDOUT-017` | Temporal Post-Cu | `False` | ✅ False | ✅ False | ✅ False | Boeing's Starliner Calypso crew capsule permanently evacuate... |
| `HOLDOUT-018` | Temporal Post-Cu | `False` | ✅ False | ❌ Unsupported | ❌ Unverifiable | The 2024 Nobel Prize in Physics was awarded for the experime... |
| `HOLDOUT-019` | Astrobiology | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ✅ Unsupported | Atmospheric biosignature disequilibrium on exoplanet K2-18b ... |
| `HOLDOUT-020` | Particle Physics | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ✅ Unsupported | Sterile right-handed neutrinos with masses near 7 keV accoun... |
| `HOLDOUT-021` | Geobiology | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ✅ Unsupported | Microbial life originated at terrestrial subaerial hot sprin... |
| `HOLDOUT-022` | Neurobiology | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ✅ Unsupported | Quantum entanglement across nuclear spins in intracellular p... |
| `HOLDOUT-023` | Archaeology | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ✅ Unsupported | Submerged Paleolithic megalithic structures in the Persian G... |
| `HOLDOUT-024` | Temporal Post-Cu | `Unsupported` | ❌ False | ✅ Unsupported | ❌ False | SpaceX Starship completed its first commercial orbital satel... |
| `HOLDOUT-025` | Temporal Post-Cu | `Unsupported` | ❌ False | ✅ Unsupported | ❌ False | An oral small-molecule GLP-1 receptor agonist received final... |
| `HOLDOUT-026` | Philosophy of Mi | `Unverifiable` | ❌ False | ❌ Unsupported | ✅ Unverifiable | The subjective qualitative experience of seeing the color re... |
| `HOLDOUT-027` | Aesthetics | `Unverifiable` | ❌ Unsupported | ✅ Unverifiable | ✅ Unverifiable | Acoustic orchestral symphony performance provides deeper aes... |
| `HOLDOUT-028` | Ethics & Law | `Unverifiable` | ✅ Unverifiable | ❌ True | ✅ Unverifiable | Autonomous lethal weapons systems are fundamentally morally ... |
| `HOLDOUT-029` | Cosmology | `Unverifiable` | ❌ False | ✅ Unverifiable | ❌ Unsupported | The total information entropy of our observable universe wil... |
| `HOLDOUT-030` | Future Ecology | `Unverifiable` | ❌ Unsupported | ❌ Unsupported | ✅ Unverifiable | Global artificial atmospheric aerosol injection will be perm... |
| `HOLDOUT-031` | Sociology | `Unverifiable` | ❌ Unsupported | ❌ Unsupported | ❌ False | Democratic governance is universally the most productive pol... |
| `HOLDOUT-032` | Personal Prefere | `Unverifiable` | ❌ Unsupported | ❌ Unsupported | ✅ Unverifiable | Handwritten correspondence conveys greater authentic persona... |
| `HOLDOUT-033` | Climate Science | `True` | ✅ True | ❌ Unsupported | ❌ Unsupported | Global warming is driving polar bears toward extinction... |
| `HOLDOUT-034` | Climate Science | `True` | ❌ False | ❌ Unsupported | ❌ False | The sun has gone into ‘lockdown’ which could cause freezing ... |
| `HOLDOUT-035` | Climate Science | `False` | ✅ False | ✅ False | ✅ False | The polar bear population has been growing.... |
| `HOLDOUT-036` | Climate Science | `False` | ❌ Unsupported | ❌ Unsupported | ✅ False | Ironic' study finds more CO2 has slightly cooled the planet... |
| `HOLDOUT-037` | Climate Science | `False` | ✅ False | ❌ Unsupported | ✅ False | Human additions of CO2 are in the margin of error of current... |
| `HOLDOUT-038` | Climate Science | `True` | ✅ True | ✅ True | ✅ True | They tell us that we are the primary forces controlling eart... |
| `HOLDOUT-039` | Climate Science | `True` | ✅ True | ❌ Unsupported | ✅ True | The Great Barrier Reef is experiencing the most widespread b... |
| `HOLDOUT-040` | Climate Science | `False` | ❌ Unsupported | ❌ Unsupported | ❌ Unverifiable | it’s not a pollutant that threatens human civilization.... |
| `HOLDOUT-041` | Climate Science | `False` | ❌ Unsupported | ❌ Unsupported | ✅ False | If CO2 was so terrible for the planet, then installing a CO2... |
| `HOLDOUT-042` | Climate Science | `False` | ❌ Unsupported | ❌ Unsupported | ✅ False | Sea level rise has been slow and a constant, pre-dating indu... |
| `HOLDOUT-043` | Climate Science | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ❌ False | Earth about to enter 30-YEAR ‘Mini Ice Age’... |
| `HOLDOUT-044` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ❌ False | Volcanoes Melting West Antarctic Glaciers, Not Global Warmin... |
| `HOLDOUT-045` | Climate Science | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ❌ False | the bushfires [in Australia] were caused by arsonists and a ... |
| `HOLDOUT-046` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ❌ Unsupported | Discovery Of Massive Volcanic CO2 Emissions Discredits Globa... |
| `HOLDOUT-047` | Climate Science | `False` | ❌ Unsupported | ❌ Unsupported | ✅ False | Harvard study finds that wind turbines create MORE global wa... |
| `HOLDOUT-048` | Climate Science | `False` | ❌ Unsupported | ❌ Unsupported | ❌ True | Ice berg melts, ocean level remains the same.... |
| `HOLDOUT-049` | Climate Science | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ✅ Unsupported | When the exact same group of 'experts' who claimed it was gl... |
| `HOLDOUT-050` | Climate Science | `False` | ❌ Unsupported | ❌ Unsupported | ❌ Unsupported | Scientists studying Antarctica sea ice warn a rise in accumu... |
| `HOLDOUT-051` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ❌ Unsupported | More than 500 scientists and professionals in climate and re... |
| `HOLDOUT-052` | Climate Science | `False` | ❌ Unsupported | ❌ Unsupported | ❌ Unsupported | Unprecedented climate change has caused sea level at Sydney ... |
| `HOLDOUT-053` | Climate Science | `False` | ❌ Unsupported | ❌ Unsupported | ✅ False | Human-produced carbon might be one of the factors [of climat... |
| `HOLDOUT-054` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ❌ False | CO2 does not cause climate change, it RESPONDS to it [...]... |
| `HOLDOUT-055` | Climate Science | `True` | ❌ False | ❌ Unsupported | ❌ False | Earth’s mean temperature over the last 2,000 years shows two... |
| `HOLDOUT-056` | Climate Science | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ❌ False | [NASA] has been adjusting temperatures from the past[...]... |
| `HOLDOUT-057` | Climate Science | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ❌ False | Fifty-five thousand years ago the whole world was 2°C warmer... |
| `HOLDOUT-058` | Climate Science | `False` | ✅ False | ✅ False | ✅ False | Sea level rise is not going to happen.... |
| `HOLDOUT-059` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ❌ False | Cold weather to grip world as solar minimum to deepen, NASA ... |
| `HOLDOUT-060` | Climate Science | `Unsupported` | ❌ False | ✅ Unsupported | ❌ True | [O]ne of the previously fastest shrinking glaciers in the wo... |
| `HOLDOUT-061` | Climate Science | `True` | ❌ False | ❌ Unsupported | ❌ False | The models predicted about three times the amount of warming... |
| `HOLDOUT-062` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ❌ Unsupported | The science is clear, climate change is making extreme weath... |
| `HOLDOUT-063` | Climate Science | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ❌ False | Burping cows are more damaging to the climate than all the c... |
| `HOLDOUT-064` | Climate Science | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ✅ Unsupported | [S]unspot activity on the surface of our star has dropped to... |
| `HOLDOUT-065` | Climate Science | `False` | ❌ Unsupported | ❌ Unsupported | ✅ False | The rate of warming according to the data is much slower tha... |
| `HOLDOUT-066` | Climate Science | `False` | ❌ True | ❌ Unsupported | ✅ False | The ­atmospheric residency time of carbon dioxide is five ye... |
| `HOLDOUT-067` | Climate Science | `False` | ✅ False | ✅ False | ✅ False | There isn’t yet any empirical evidence for their claim that ... |
| `HOLDOUT-068` | Climate Science | `Unsupported` | ❌ False | ❌ False | ❌ False | NOAA has adjusted past temperatures to look colder than they... |
| `HOLDOUT-069` | Climate Science | `Unsupported` | ❌ Unverifiable | ✅ Unsupported | ❌ Unverifiable | They were going to be gone by now, but now they're setting r... |
| `HOLDOUT-070` | Climate Science | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ❌ False | unadjusted data suggests that temperatures in Australia have... |
| `HOLDOUT-071` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ✅ True | [climate scientists] say that aspects of the case of Hurrica... |
| `HOLDOUT-072` | Climate Science | `False` | ✅ False | ✅ False | ✅ False | The IPCC, the Intergovernmental Panel on Climate Change, whi... |
| `HOLDOUT-073` | Climate Science | `False` | ✅ False | ✅ False | ✅ False | according, again, to the official figures—during this past 1... |
| `HOLDOUT-074` | Climate Science | `Unsupported` | ❌ Unverifiable | ✅ Unsupported | ❌ False | Trump's action could push the Earth over the brink, to becom... |
| `HOLDOUT-075` | Climate Science | `True` | ❌ False | ❌ Unsupported | ❌ Unsupported | Most likely the primary control knob [on climate change] is ... |
| `HOLDOUT-076` | Climate Science | `True` | ❌ False | ❌ False | ❌ False | 'Global warming' is a myth — so say 80 graphs from 58 peer-r... |
| `HOLDOUT-077` | Climate Science | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ❌ False | Neither the rate nor the magnitude of the reported late twen... |
| `HOLDOUT-078` | Climate Science | `Unsupported` | ❌ False | ❌ False | ❌ False | Forward projections of solar cyclicity imply the next few de... |
| `HOLDOUT-079` | Climate Science | `False` | ✅ False | ✅ False | ✅ False | global warming ceased around the end of the twentieth centur... |
| `HOLDOUT-080` | Climate Science | `True` | ❌ False | ❌ False | ❌ False | Increases in atmospheric CO2 followed increases in temperatu... |
| `HOLDOUT-081` | Climate Science | `False` | ✅ False | ✅ False | ✅ False | Therefore, CO2 levels could not have forced temperatures to ... |
| `HOLDOUT-082` | Climate Science | `True` | ✅ True | ❌ Unsupported | ✅ True | Local and regional sea levels continue to exhibit typical na... |
| `HOLDOUT-083` | Climate Science | `False` | ❌ Unsupported | ❌ Unsupported | ✅ False | The temperature is not rising nearly as fast as the alarmist... |
| `HOLDOUT-084` | Climate Science | `True` | ❌ False | ❌ Unsupported | ✅ True | more than 100 per cent of the warming over the past century ... |
| `HOLDOUT-085` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ❌ Unsupported | 90 per cent of the world's coral reefs will disappear in the... |
| `HOLDOUT-086` | Climate Science | `False` | ✅ False | ❌ Unsupported | ✅ False | El Niño drove record highs in global temperatures suggesting... |
| `HOLDOUT-087` | Climate Science | `False` | ❌ Unsupported | ❌ Unsupported | ❌ True | Increased atmospheric carbon dioxide has helped raise global... |
| `HOLDOUT-088` | Climate Science | `Unsupported` | ❌ False | ❌ False | ❌ False | Sea level rise, which was occurring long before humans could... |
| `HOLDOUT-089` | Climate Science | `Unsupported` | ❌ True | ✅ Unsupported | ✅ Unsupported | Sea level rise could reach six or seven feet by the year 210... |
| `HOLDOUT-090` | Climate Science | `Unsupported` | ❌ False | ❌ False | ❌ False | Climate change is not making natural disasters worse... |
| `HOLDOUT-091` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ❌ False | The amount of land we use for meat — humankind’s biggest use... |
| `HOLDOUT-092` | Climate Science | `True` | ✅ True | ❌ Unsupported | ✅ True | Carbon emissions are declining in most rich nations and have... |
| `HOLDOUT-093` | Climate Science | `False` | ✅ False | ❌ Unsupported | ❌ Unverifiable | Preventing future pandemics requires more not less “industri... |
| `HOLDOUT-094` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ❌ False | As a result, half of the people surveyed around the world la... |
| `HOLDOUT-095` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ✅ True | And in January, one out of five British children told pollst... |
| `HOLDOUT-096` | Climate Science | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ❌ True | Greenpeace didn’t save the whales, switching from whale oil ... |
| `HOLDOUT-097` | Climate Science | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ❌ True | Worst-case global heating scenarios may need to be revised u... |
| `HOLDOUT-098` | Climate Science | `Unsupported` | ✅ Unsupported | ✅ Unsupported | ❌ True | Recent modelling data suggests the climate is considerably m... |
| `HOLDOUT-099` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ✅ True | Previous IPCC reports tended to assume that clouds would hav... |
| `HOLDOUT-100` | Climate Science | `True` | ❌ Unsupported | ❌ Unsupported | ✅ True | “Catherine Senior, head of understanding climate change at t... |
