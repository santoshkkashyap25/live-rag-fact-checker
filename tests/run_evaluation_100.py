# tests/run_evaluation_100.py
"""
FactGuard AI - 100-Claim Statistically Powered Benchmark Runner (N = 100)
Evaluates on balanced 10-domain dataset:
- 40 True Claims (FEVER + Scientific Ground Truth)
- 40 False Claims (TruthfulQA Misconceptions + FEVER Refutes)
- 20 Unverifiable Claims (Future Speculation, Subjective Aesthetics, Epistemic Uncertainty)

Outputs:
- Frozen Evidence Cache (tests/data/frozen_evidence_100.json)
- Raw Evaluation Telemetry (tests/data/eval_results_100.json)
- Full Evaluation Report (tests/evaluation_report_100.md)
- McNemar Paired Chi-Square Tests with Edwards Continuity Correction (p-value)
"""

import os
import sys
import json
import time
import math
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Setup environment & import backend
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")
load_dotenv()

from core.claim_extractor import claim_extractor
from core.web_search import web_search
from core.re_ranker import re_ranker
from core.llm_service import llm_service
from config import TOP_K_RETRIEVE, TOP_K_RERANK_RESULTS

DATA_DIR = Path(__file__).resolve().parent / "data"
TEST_100_PATH = DATA_DIR / "claims_test_100.json"
FROZEN_EVIDENCE_100_PATH = DATA_DIR / "frozen_evidence_100.json"
EVAL_RESULTS_100_PATH = DATA_DIR / "eval_results_100.json"
REPORT_100_PATH = Path(__file__).resolve().parent / "evaluation_report_100.md"


# --- 1. Statistical Calculations ---

def compute_wilson_ci(p_hat: float, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Calculate Wilson score 95% confidence interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    denominator = 1.0 + (z**2) / n
    centre_adjusted_probability = p_hat + (z**2) / (2 * n)
    adjusted_standard_deviation = math.sqrt((p_hat * (1 - p_hat) + (z**2) / (4 * n)) / n)
    lower = (centre_adjusted_probability - z * adjusted_standard_deviation) / denominator
    upper = (centre_adjusted_probability + z * adjusted_standard_deviation) / denominator
    return (max(0.0, lower), min(1.0, upper))


def compute_mcnemar_test(results_a: List[Dict[str, Any]], results_b: List[Dict[str, Any]]) -> Dict[str, Any]:
    """McNemar's paired test with Edwards continuity correction."""
    map_a = {r["id"]: r["is_correct"] for r in results_a}
    map_b = {r["id"]: r["is_correct"] for r in results_b}

    both_correct = 0
    a_only = 0
    b_only = 0
    both_wrong = 0

    for cid in map_a:
        if cid in map_b:
            corr_a = map_a[cid]
            corr_b = map_b[cid]
            if corr_a and corr_b:
                both_correct += 1
            elif corr_a and not corr_b:
                a_only += 1
            elif not corr_a and corr_b:
                b_only += 1
            else:
                both_wrong += 1

    discordant = a_only + b_only
    if discordant == 0:
        chi2 = 0.0
        p_val = 1.0
    else:
        chi2 = ((abs(a_only - b_only) - 1.0) ** 2) / discordant
        p_val = math.erfc(math.sqrt(chi2) / math.sqrt(2))

    return {
        "contingency_matrix": {
            "both_correct": both_correct,
            "model_a_only": a_only,
            "model_b_only": b_only,
            "both_wrong": both_wrong
        },
        "discordant_pairs": discordant,
        "chi2": round(chi2, 4),
        "p_value": round(p_val, 5),
        "statistically_significant_05": p_val < 0.05,
        "statistically_significant_01": p_val < 0.01
    }


def compute_calibration(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate calibration bins and Expected Calibration Error (ECE)."""
    bins = [
        {"min": 0.0, "max": 0.5, "label": "0.00 - 0.50"},
        {"min": 0.5, "max": 0.7, "label": "0.50 - 0.70"},
        {"min": 0.7, "max": 0.85, "label": "0.70 - 0.85"},
        {"min": 0.85, "max": 0.95, "label": "0.85 - 0.95"},
        {"min": 0.95, "max": 1.01, "label": "0.95 - 1.00"}
    ]
    total = len(results)
    if total == 0:
        return {"ece": 0.0, "bins": []}

    ece = 0.0
    bin_stats = []
    for b in bins:
        items = [r for r in results if b["min"] <= r.get("confidence", 0.0) < b["max"]]
        count = len(items)
        if count > 0:
            avg_conf = sum(r.get("confidence", 0.0) for r in items) / count
            acc = sum(1 for r in items if r["is_correct"]) / count
            gap = abs(acc - avg_conf)
            ece += (count / total) * gap
            bin_stats.append({
                "bin": b["label"],
                "count": count,
                "avg_confidence": round(avg_conf, 3),
                "empirical_accuracy": round(acc, 3),
                "gap": round(gap, 3)
            })
        else:
            bin_stats.append({
                "bin": b["label"],
                "count": 0,
                "avg_confidence": 0.0,
                "empirical_accuracy": 0.0,
                "gap": 0.0
            })
    return {"ece": round(ece, 4), "bins": bin_stats}


# --- 2. Evidence Freezing ---

def freeze_all_evidence_100(claims: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Pre-fetch and persist web retrieval evidence to disk using async search engine."""
    cache: Dict[str, List[Dict[str, Any]]] = {}
    if FROZEN_EVIDENCE_100_PATH.exists():
        try:
            with open(FROZEN_EVIDENCE_100_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
            print(f"📦 Loaded {len(cache)} existing frozen evidence items from disk.")
        except Exception as e:
            print(f"Warning loading cache: {e}")

    updated = False
    for i, item in enumerate(claims, 1):
        cid = item.get("id") or item["claim"]
        if cid not in cache:
            claim_text = item["claim"]
            print(f"  🔍 [{i}/{len(claims)}] Fetching evidence for [{cid}]: {claim_text[:50]}...")
            extracted = claim_extractor.extract(claim_text)
            results = web_search.search(extracted, max_results=TOP_K_RETRIEVE)
            cache[cid] = results
            updated = True
            time.sleep(0.3)

    if updated:
        FROZEN_EVIDENCE_100_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(FROZEN_EVIDENCE_100_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
        print(f"✅ Frozen evidence successfully saved ({len(cache)} claims cached).")

    return cache


# --- 3. Configuration Evaluator ---

def evaluate_single_100(
    claim_dict: Dict[str, Any],
    config: str,
    frozen_evidence: List[Dict[str, Any]]
) -> Dict[str, Any]:
    raw_text = claim_dict["claim"]
    start_t = time.time()

    # 1. Baseline: Zero-shot ungrounded LLM
    if config == "baseline_ungrounded":
        v, c, r = "Unverifiable", 0.0, "Execution failed"
        for attempt in range(4):
            try:
                res = llm_service.get_verdict(raw_text, evidence=[], provider="groq")
                v, c, r = res.verdict, res.confidence, res.reasoning
                if "Rate limit" in r or "rate_limit_exceeded" in r or "429" in r:
                    time.sleep(5.0 * (attempt + 1))
                    continue
                break
            except Exception as e:
                if "429" in str(e):
                    time.sleep(5.0 * (attempt + 1))
                    continue
                v, c, r = "Unverifiable", 0.0, str(e)
                break
        return {
            "verdict": v,
            "confidence": c,
            "reasoning": r,
            "evidence_count": 0,
            "latency": time.time() - start_t
        }

    # Query extraction or raw
    query = raw_text if config == "baseline_raw_search" else claim_extractor.extract(raw_text)

    # Re-ranking / Filtering
    evidence_pool = list(frozen_evidence)
    if config == "baseline_raw_search":
        selected_pairs = [(e, 1.0) for e in evidence_pool[:TOP_K_RERANK_RESULTS]]
    else:
        selected_pairs = re_ranker.rerank_items(query, evidence_pool, top_k=TOP_K_RERANK_RESULTS)

    # Format formatted evidence snippets
    evidence_items = []
    for item, _ in selected_pairs:
        title = item.get("title", "Web Source")
        snippet = item.get("snippet", "")
        trust = item.get("domain_trust", {})
        badge = trust.get("badge", item.get("source", "Web"))
        if trust.get("is_satire"):
            evidence_items.append(f"[{title} | ⚠️ SATIRE SOURCE] {snippet}")
        else:
            evidence_items.append(f"[{title} | {badge}] {snippet}")

    # LLM Verification with exponential backoff on 429
    v, c, r = "Unverifiable", 0.0, "Execution failed"
    for attempt in range(4):
        try:
            verdict_obj = llm_service.get_verdict(
                claim=query,
                evidence=evidence_items,
                provider="groq"
            )
            v = verdict_obj.verdict
            c = verdict_obj.confidence
            r = verdict_obj.reasoning
            if "Rate limit" in r or "rate_limit_exceeded" in r or "429" in r:
                time.sleep(5.0 * (attempt + 1))
                continue
            break
        except Exception as e:
            if "429" in str(e):
                time.sleep(5.0 * (attempt + 1))
                continue
            v, c, r = "Unverifiable", 0.0, str(e)
            break

    return {
        "verdict": v,
        "confidence": c,
        "reasoning": r,
        "evidence_count": len(evidence_items),
        "latency": time.time() - start_t
    }


def compute_metrics_100(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    if total == 0:
        return {}

    classes = ["True", "False", "Unverifiable"]
    cm = {exp: {pred: 0 for pred in classes} for exp in classes}
    correct = 0
    answered = 0
    answered_correct = 0

    for r in results:
        exp = r["expected"]
        pred = r["verdict"]
        if exp in cm and pred in cm[exp]:
            cm[exp][pred] += 1
        if pred == exp:
            correct += 1
        if pred in ("True", "False"):
            answered += 1
            if pred == exp:
                answered_correct += 1

    accuracy = correct / total
    acc_ci_low, acc_ci_high = compute_wilson_ci(accuracy, total)
    coverage = answered / total
    selective_acc = (answered_correct / answered) if answered > 0 else 0.0

    f1s = []
    for c in classes:
        tp = cm[c][c]
        fp = sum(cm[o][c] for o in classes if o != c)
        fn = sum(cm[c][o] for o in classes if o != c)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        f1s.append(f1)
    macro_f1 = sum(f1s) / len(f1s)

    latencies = [r.get("latency", 0.0) for r in results]
    latencies.sort()
    p50 = latencies[len(latencies) // 2] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    return {
        "total": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "accuracy_ci_95": (round(acc_ci_low, 4), round(acc_ci_high, 4)),
        "coverage": round(coverage, 4),
        "selective_accuracy": round(selective_acc, 4),
        "macro_f1": round(macro_f1, 4),
        "confusion_matrix": cm,
        "p50_latency": round(p50, 2),
        "p95_latency": round(p95, 2),
        "false_positives": cm["False"]["True"],
        "false_negatives": cm["True"]["False"],
        "unverifiable_count": sum(cm[c]["Unverifiable"] for c in classes)
    }


# --- 4. Main Execution & Report Generation ---

def main():
    print("=" * 80)
    print("🔬 FactGuard AI: 100-Claim Statistically Powered Benchmark Runner (N = 100)")
    print("=" * 80)

    # 1. Load Data
    with open(TEST_100_PATH, "r", encoding="utf-8") as f:
        claims = json.load(f)
    print(f"Loaded {len(claims)} Benchmark Claims (40 True, 40 False, 20 Unverifiable)")

    # 2. Freeze evidence
    frozen_evidence = freeze_all_evidence_100(claims)

    configs_to_run = ["factguard_full", "baseline_raw_search", "baseline_ungrounded"]
    all_eval_data: Dict[str, Any] = {
        "test": {},
        "metrics": {},
        "statistical_tests": {},
        "calibration": {},
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }

    # Run evaluations
    for cfg in configs_to_run:
        print(f"\n--- Evaluating Config: {cfg} (100 claims) ---")
        results = []
        for i, c in enumerate(claims, 1):
            ev = frozen_evidence.get(c["id"], [])
            res = evaluate_single_100(c, cfg, ev)
            res.update({
                "id": c["id"],
                "claim": c["claim"],
                "expected": c["expected"],
                "domain": c.get("domain", "General"),
                "is_correct": (res["verdict"] == c["expected"])
            })
            results.append(res)
            if i % 10 == 0:
                print(f"  Processed {i}/100 claims ({res['id']} got {res['verdict']} vs {res['expected']})...")
            time.sleep(0.3)
        all_eval_data["test"][cfg] = results
        all_eval_data["metrics"][cfg] = compute_metrics_100(results)

    # McNemar's paired test
    fg_res = all_eval_data["test"]["factguard_full"]
    raw_res = all_eval_data["test"]["baseline_raw_search"]
    ungrounded_res = all_eval_data["test"]["baseline_ungrounded"]

    mcnemar_raw = compute_mcnemar_test(fg_res, raw_res)
    mcnemar_ungrounded = compute_mcnemar_test(fg_res, ungrounded_res)

    all_eval_data["statistical_tests"]["fg_vs_raw_search"] = mcnemar_raw
    all_eval_data["statistical_tests"]["fg_vs_ungrounded"] = mcnemar_ungrounded
    all_eval_data["calibration"]["factguard_full"] = compute_calibration(fg_res)

    print("\n--- Statistical Test Results ---")
    print(f"  FactGuard vs Raw Search: p = {mcnemar_raw['p_value']}, chi2 = {mcnemar_raw['chi2']} (discordant: {mcnemar_raw['discordant_pairs']})")
    print(f"  FactGuard vs Ungrounded: p = {mcnemar_ungrounded['p_value']}, chi2 = {mcnemar_ungrounded['chi2']} (discordant: {mcnemar_ungrounded['discordant_pairs']})")

    # Save results
    with open(EVAL_RESULTS_100_PATH, "w", encoding="utf-8") as f:
        json.dump(all_eval_data, f, indent=2)
    print(f"\n💾 Saved complete results to {EVAL_RESULTS_100_PATH}")

    # Generate Report
    generate_markdown_report_100(all_eval_data, REPORT_100_PATH)
    print(f"📄 Generated 100-claim evaluation report at {REPORT_100_PATH}")


def generate_markdown_report_100(data: Dict[str, Any], output_path: Path):
    m = data["metrics"]
    fg = m.get("factguard_full", {})
    raw = m.get("baseline_raw_search", {})
    ungrounded = m.get("baseline_ungrounded", {})

    fg_vs_raw = data["statistical_tests"]["fg_vs_raw_search"]
    fg_vs_ungrounded = data["statistical_tests"]["fg_vs_ungrounded"]

    report = f"""# FactGuard AI: 100-Claim Statistically Powered Benchmark Report
**Timestamp**: {data['timestamp']}  
**Evaluation Protocol**: Frozen Evidence Benchmark on 100 Balanced Claims ($N = 100$)  
**Dataset Architecture**: 40 True, 40 False, 20 Unverifiable across 10 academic domains  
**Evaluated Model**: Groq LPU `openai/gpt-oss-120b` (temperature = 0.2, max_tokens = 1536, single deterministic run)  
**Retrieval Engine**: Multi-Engine Async Web Search (DuckDuckGo + Wikipedia + Instant Answers, frozen cache)  

---

## 1. Executive Summary & Comparative Headline Performance ($N = 100$)

| System Configuration | Accuracy | 95% Wilson CI | Coverage | Selective Acc | Macro-F1 | p50 Latency (Frozen) | McNemar Paired Test |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FactGuard AI (Full Pipeline)** | **{fg.get('accuracy', 0)*100:.1f}% ({fg.get('correct', 0)}/100)** | [{fg.get('accuracy_ci_95', [0,0])[0]*100:.1f}%, {fg.get('accuracy_ci_95', [0,0])[1]*100:.1f}%] | **{fg.get('coverage', 0)*100:.1f}%** | **{fg.get('selective_accuracy', 0)*100:.1f}%** | **{fg.get('macro_f1', 0):.3f}** | {fg.get('p50_latency', 0):.2f}s | — |
| Raw Web Search + LLM Baseline | {raw.get('accuracy', 0)*100:.1f}% ({raw.get('correct', 0)}/100) | [{raw.get('accuracy_ci_95', [0,0])[0]*100:.1f}%, {raw.get('accuracy_ci_95', [0,0])[1]*100:.1f}%] | {raw.get('coverage', 0)*100:.1f}% | {raw.get('selective_accuracy', 0)*100:.1f}% | {raw.get('macro_f1', 0):.3f} | {raw.get('p50_latency', 0):.2f}s | $\\chi^2 = {fg_vs_raw['chi2']}, p = {fg_vs_raw['p_value']}$ |
| Ungrounded Zero-Shot LLM | {ungrounded.get('accuracy', 0)*100:.1f}% ({ungrounded.get('correct', 0)}/100) | [{ungrounded.get('accuracy_ci_95', [0,0])[0]*100:.1f}%, {ungrounded.get('accuracy_ci_95', [0,0])[1]*100:.1f}%] | {ungrounded.get('coverage', 0)*100:.1f}% | {ungrounded.get('selective_accuracy', 0)*100:.1f}% | {ungrounded.get('macro_f1', 0):.3f} | {ungrounded.get('p50_latency', 0):.2f}s | $\\chi^2 = {fg_vs_ungrounded['chi2']}, p = {fg_vs_ungrounded['p_value']}$ |

---

## 2. Statistical Significance Analysis (McNemar's Paired Test)

With $N = 100$ claims and substantial discordant pairs, McNemar's test measures whether FactGuard AI's accuracy advantage is statistically significant:

- **FactGuard AI vs. Raw Web Search + LLM**:
  - Contingency: Both Correct = {fg_vs_raw['contingency_matrix']['both_correct']}, FG Only = {fg_vs_raw['contingency_matrix']['model_a_only']}, Raw Only = {fg_vs_raw['contingency_matrix']['model_b_only']}, Both Wrong/Abstained = {fg_vs_raw['contingency_matrix']['both_wrong']}
  - Discordant Claims ($b + c$): {fg_vs_raw['discordant_pairs']}
  - $\\chi^2 = {fg_vs_raw['chi2']}$, **$p$-value = {fg_vs_raw['p_value']}** (Statistically significant at $\\alpha = 0.05$: {fg_vs_raw['statistically_significant_05']})

- **FactGuard AI vs. Zero-Shot Ungrounded LLM**:
  - Contingency: Both Correct = {fg_vs_ungrounded['contingency_matrix']['both_correct']}, FG Only = {fg_vs_ungrounded['contingency_matrix']['model_a_only']}, LLM Only = {fg_vs_ungrounded['contingency_matrix']['model_b_only']}, Both Wrong/Abstained = {fg_vs_ungrounded['contingency_matrix']['both_wrong']}
  - Discordant Claims ($b + c$): {fg_vs_ungrounded['discordant_pairs']}
  - $\\chi^2 = {fg_vs_ungrounded['chi2']}$, **$p$-value = {fg_vs_ungrounded['p_value']}** (Statistically significant at $\\alpha = 0.01$: {fg_vs_ungrounded['statistically_significant_01']})

---

## 3. Confusion Matrix Breakdown (FactGuard Full, $N = 100$)

```
                           PREDICTED VERDICT
                   True         False      Unverifiable    Total
EXPECTED  True       {fg.get('confusion_matrix', {}).get('True', {}).get('True', 0):<12} {fg.get('confusion_matrix', {}).get('True', {}).get('False', 0):<12} {fg.get('confusion_matrix', {}).get('True', {}).get('Unverifiable', 0):<12} 40
VERDICT   False      {fg.get('confusion_matrix', {}).get('False', {}).get('True', 0):<12} {fg.get('confusion_matrix', {}).get('False', {}).get('False', 0):<12} {fg.get('confusion_matrix', {}).get('False', {}).get('Unverifiable', 0):<12} 40
          Unverif.   {fg.get('confusion_matrix', {}).get('Unverifiable', {}).get('True', 0):<12} {fg.get('confusion_matrix', {}).get('Unverifiable', {}).get('False', 0):<12} {fg.get('confusion_matrix', {}).get('Unverifiable', {}).get('Unverifiable', 0):<12} 20
          Total      {sum(fg.get('confusion_matrix', {}).get(r, {}).get('True', 0) for r in ['True','False','Unverifiable']):<12} {sum(fg.get('confusion_matrix', {}).get(r, {}).get('False', 0) for r in ['True','False','Unverifiable']):<12} {sum(fg.get('confusion_matrix', {}).get(r, {}).get('Unverifiable', 0) for r in ['True','False','Unverifiable']):<12} 100
```

- **False Positives (False claim marked True)**: {fg.get('false_positives', 0)} ({fg.get('false_positives', 0)/40*100:.1f}%)
- **False Negatives (True claim marked False)**: {fg.get('false_negatives', 0)} ({fg.get('false_negatives', 0)/40*100:.1f}%)
- **Unverifiable Abstentions**: {fg.get('unverifiable_count', 0)}

---

## 4. Confidence Calibration ($N = 100$, ECE = {data['calibration']['factguard_full']['ece']})

| Confidence Bin | Claim Count | Mean Predicted Confidence | Empirical Accuracy | Calibration Gap |
| :--- | :--- | :--- | :--- | :--- |
"""
    for b in data['calibration']['factguard_full']['bins']:
        report += f"| {b['bin']} | {b['count']} | {b['avg_confidence']*100:.1f}% | {b['empirical_accuracy']*100:.1f}% | {b['gap']*100:.1f}% |\n"

    report += f"""
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
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)


if __name__ == "__main__":
    main()
