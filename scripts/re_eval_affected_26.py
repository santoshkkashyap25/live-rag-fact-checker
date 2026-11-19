"""
Re-evaluate the 26 claims affected by Groq 429 rate limit fallbacks during the N=300 evaluation.
Uses frozen web evidence and updated llm_service with exponential backoff and allow_fallback=False.
"""

import os
import sys
import json
import time
import math
from typing import List, Dict, Any

# Ensure project root and backend are on sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")
sys.path.insert(0, root_dir)
sys.path.insert(0, backend_dir)

from core.llm_service import llm_service
from core.re_ranker import re_ranker

CLASSES = ["True", "False", "Unsupported", "Unverifiable"]

ZERO_SHOT_PROMPT = """You are FactGuard AI, an expert analytical fact-checker.
Evaluate the following factual claim using your comprehensive scientific, historical, and general world knowledge.

EPISTEMIC STANDARDS:
1. 'True': The assertion is an established, verifiable factual truth supported by scientific consensus or historical records.
2. 'False': The assertion is an established falsehood, misconception, refuted myth, or factually inaccurate.
3. 'Unsupported': The assertion is an unverified empirical hypothesis, active scientific conjecture, or speculative rumor lacking conclusive confirmation.
4. 'Unverifiable': The assertion is inherently non-falsifiable in principle (subjective taste, aesthetic preference, normative moral/ethical judgment, or future prediction).

Return valid JSON with:
{{
  "verdict": "True" | "False" | "Unsupported" | "Unverifiable",
  "confidence": 0.0 to 1.0,
  "reasoning": "Clear 1-2 sentence factual explanation."
}}

CLAIM: "{claim}"
"""


def wilson_score_interval(k: int, n: int, confidence: float = 0.95) -> List[float]:
    if n == 0:
        return [0.0, 0.0]
    z = 1.959963984540054
    p = k / n
    denom = 1.0 + z**2 / n
    center = (p + z**2 / (2.0 * n)) / denom
    spread = (z * math.sqrt((p * (1.0 - p) + z**2 / (4.0 * n)) / n)) / denom
    return [max(0.0, center - spread), min(1.0, center + spread)]


def evaluate_factguard_safe(claim_text: str, raw_evidence: List[Dict[str, str]]) -> Dict[str, Any]:
    evidence_pool = list(raw_evidence)
    selected_pairs = re_ranker.rerank_items(claim_text, evidence_pool, top_k=5)

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

    for retry_loop in range(10):
        try:
            t0 = time.time()
            verdict_obj = llm_service.get_verdict(
                claim=claim_text,
                evidence=evidence_items,
                provider="groq",
                allow_fallback=False
            )
            elapsed = time.time() - t0
            return {
                "verdict": verdict_obj.verdict,
                "confidence": verdict_obj.confidence,
                "reasoning": verdict_obj.reasoning,
                "evidence_used": evidence_items,
                "latency_sec": elapsed,
                "model": verdict_obj.model_used,
                "prompt_version": verdict_obj.prompt_version,
                "prompt_hash": verdict_obj.prompt_hash
            }
        except Exception as e:
            wait = 5.0 * (retry_loop + 1)
            print(f"    [Retry FG {retry_loop+1}] Error: {str(e)[:70]}. Sleeping {wait}s...")
            time.sleep(wait)


def evaluate_raw_search_safe(claim_text: str, raw_evidence: List[Dict[str, str]]) -> Dict[str, Any]:
    raw_docs = []
    for item in raw_evidence[:4]:
        title = item.get("title", "Web Source")
        snippet = item.get("snippet", "")
        raw_docs.append(f"[{title}] {snippet}")

    for retry_loop in range(10):
        try:
            t0 = time.time()
            verdict_obj = llm_service.get_verdict(
                claim=claim_text,
                evidence=raw_docs,
                provider="groq",
                allow_fallback=False
            )
            elapsed = time.time() - t0
            return {
                "verdict": verdict_obj.verdict,
                "confidence": verdict_obj.confidence,
                "reasoning": verdict_obj.reasoning,
                "evidence_used": raw_docs,
                "latency_sec": elapsed,
                "model": verdict_obj.model_used,
                "prompt_version": verdict_obj.prompt_version
            }
        except Exception as e:
            wait = 5.0 * (retry_loop + 1)
            print(f"    [Retry Raw {retry_loop+1}] Error: {str(e)[:70]}. Sleeping {wait}s...")
            time.sleep(wait)


def evaluate_zero_shot_safe(claim_text: str) -> Dict[str, Any]:
    for retry_loop in range(10):
        try:
            t0 = time.time()
            verdict_obj = llm_service.get_verdict(
                claim=claim_text,
                evidence=[],
                provider="groq",
                prompt_template=ZERO_SHOT_PROMPT,
                allow_fallback=False
            )
            elapsed = time.time() - t0
            return {
                "verdict": verdict_obj.verdict,
                "confidence": verdict_obj.confidence,
                "reasoning": verdict_obj.reasoning,
                "latency_sec": elapsed,
                "model": verdict_obj.model_used
            }
        except Exception as e:
            wait = 5.0 * (retry_loop + 1)
            print(f"    [Retry ZS {retry_loop+1}] Error: {str(e)[:70]}. Sleeping {wait}s...")
            time.sleep(wait)


def compute_system_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    correct_4class = 0
    correct_3class = 0
    decisive_total = 0
    decisive_correct = 0

    matrix_4class = {c: {c2: 0 for c2 in CLASSES} for c in CLASSES}
    matrix_3class = {"SUPPORTS": {"SUPPORTS": 0, "REFUTES": 0, "NEI": 0},
                     "REFUTES": {"SUPPORTS": 0, "REFUTES": 0, "NEI": 0},
                     "NEI": {"SUPPORTS": 0, "REFUTES": 0, "NEI": 0}}

    for r in results:
        expected = r["expected"]
        pred = r["verdict"]

        if pred not in CLASSES:
            pred = "Unsupported"

        matrix_4class[expected][pred] += 1
        if pred == expected:
            correct_4class += 1

        if pred in ["True", "False"]:
            decisive_total += 1
            if pred == expected:
                decisive_correct += 1

        exp_3 = "SUPPORTS" if expected == "True" else ("REFUTES" if expected == "False" else "NEI")
        pred_3 = "SUPPORTS" if pred == "True" else ("REFUTES" if pred == "False" else "NEI")
        matrix_3class[exp_3][pred_3] += 1
        if pred_3 == exp_3:
            correct_3class += 1

    acc_4 = correct_4class / total if total > 0 else 0.0
    low_4, high_4 = wilson_score_interval(correct_4class, total)

    acc_3 = correct_3class / total if total > 0 else 0.0
    low_3, high_3 = wilson_score_interval(correct_3class, total)

    coverage = decisive_total / total if total > 0 else 0.0
    selective_prec = decisive_correct / decisive_total if decisive_total > 0 else 0.0

    return {
        "total": total,
        "correct_4class": correct_4class,
        "accuracy_4class": acc_4,
        "accuracy_4class_ci": [low_4, high_4],
        "correct_3class": correct_3class,
        "accuracy_3class": acc_3,
        "accuracy_3class_ci": [low_3, high_3],
        "decisive_count": decisive_total,
        "coverage": coverage,
        "selective_precision": selective_prec,
        "matrix_4class": matrix_4class,
        "matrix_3class": matrix_3class
    }


def compute_mcnemar(results_a: List[Dict[str, Any]], results_b: List[Dict[str, Any]]) -> Dict[str, Any]:
    b = 0
    c = 0
    both_correct = 0
    both_wrong = 0

    for ra, rb in zip(results_a, results_b):
        a_ok = (ra["verdict"] == ra["expected"])
        b_ok = (rb["verdict"] == rb["expected"])

        if a_ok and b_ok:
            both_correct += 1
        elif not a_ok and not b_ok:
            both_wrong += 1
        elif a_ok and not b_ok:
            b += 1
        else:
            c += 1

    discordant = b + c
    if discordant == 0:
        chi2 = 0.0
        p_val = 1.0
    else:
        chi2 = (abs(b - c) - 1.0)**2 / discordant if abs(b - c) > 1 else 0.0
        k = min(b, c)
        p_val = min(1.0, 2.0 * sum(math.comb(discordant, i) * (0.5**discordant) for i in range(k + 1)))

    return {
        "system_a_only": b,
        "system_b_only": c,
        "both_correct": both_correct,
        "both_wrong": both_wrong,
        "discordant_pairs": discordant,
        "chi2": chi2,
        "p_value": p_val
    }


def generate_markdown_report(report_path: str, claims_count: int, m_fg: Dict[str, Any], m_raw: Dict[str, Any], m_zs: Dict[str, Any],
                             mc_raw: Dict[str, Any], mc_zs: Dict[str, Any], records: List[Dict[str, Any]]):
    md = f"""# FactGuard AI: Scaled Scientific Evaluation Report (N = {claims_count})

> **Evaluation Standard**: Strictly held-out, decontaminated benchmark suite ($N = {claims_count}$). All claims were decontaminated against the 1,016 development claims using Levenshtein distance filtering ($< 0.60$). Evaluated with **frozen multi-engine web evidence** across all systems to eliminate retrieval drift.

---

## 1. Headline Empirical Comparison

| System Configuration | 4-Class Accuracy | 95% Wilson CI | FEVER 3-Class Accuracy | Coverage (Decisive) | Selective Precision |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **{m_fg['accuracy_4class']*100:.1f}% ({m_fg['correct_4class']}/{claims_count})** | [{m_fg['accuracy_4class_ci'][0]*100:.1f}%, {m_fg['accuracy_4class_ci'][1]*100:.1f}%] | **{m_fg['accuracy_3class']*100:.1f}%** | **{m_fg['coverage']*100:.1f}%** ({m_fg['decisive_count']}/{claims_count}) | **{m_fg['selective_precision']*100:.1f}%** |
| Raw Web Search + LLM Baseline | {m_raw['accuracy_4class']*100:.1f}% ({m_raw['correct_4class']}/{claims_count}) | [{m_raw['accuracy_4class_ci'][0]*100:.1f}%, {m_raw['accuracy_4class_ci'][1]*100:.1f}%] | {m_raw['accuracy_3class']*100:.1f}% | {m_raw['coverage']*100:.1f}% ({m_raw['decisive_count']}/{claims_count}) | {m_raw['selective_precision']*100:.1f}% |
| Fair Ungrounded Zero-Shot LLM | {m_zs['accuracy_4class']*100:.1f}% ({m_zs['correct_4class']}/{claims_count}) | [{m_zs['accuracy_4class_ci'][0]*100:.1f}%, {m_zs['accuracy_4class_ci'][1]*100:.1f}%] | {m_zs['accuracy_3class']*100:.1f}% | {m_zs['coverage']*100:.1f}% ({m_zs['decisive_count']}/{claims_count}) | {m_zs['selective_precision']*100:.1f}% |

---

## 2. Statistical Significance (Paired Tests)

* **FactGuard AI vs. Raw Web Search Baseline**:
  - Both Correct: `{mc_raw['both_correct']}`
  - Both Wrong: `{mc_raw['both_wrong']}`
  - FactGuard Only ($b$): `{mc_raw['system_a_only']}`
  - Raw Search Only ($c$): `{mc_raw['system_b_only']}`
  - Discordant Pairs: `{mc_raw['discordant_pairs']}`
  - McNemar Statistic ($\chi^2$): `{mc_raw['chi2']:.3f}`
  - Exact Binomial p-value: **p = {mc_raw['p_value']:.4f}**

* **FactGuard AI vs. Fair Ungrounded Zero-Shot Baseline**:
  - Both Correct: `{mc_zs['both_correct']}`
  - Both Wrong: `{mc_zs['both_wrong']}`
  - FactGuard Only ($b$): `{mc_zs['system_a_only']}`
  - Zero-Shot Only ($c$): `{mc_zs['system_b_only']}`
  - Discordant Pairs: `{mc_zs['discordant_pairs']}`
  - McNemar Statistic ($\chi^2$): `{mc_zs['chi2']:.3f}`
  - Exact Binomial p-value: **p = {mc_zs['p_value']:.4f}**

---

## 3. 4x4 Confusion Matrices

### FactGuard AI (Full Pipeline)
| Ground Truth \\ Predicted | True | False | Unsupported | Unverifiable | Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True** | **{m_fg['matrix_4class']['True']['True']}** | {m_fg['matrix_4class']['True']['False']} | {m_fg['matrix_4class']['True']['Unsupported']} | {m_fg['matrix_4class']['True']['Unverifiable']} | {sum(m_fg['matrix_4class']['True'].values())} |
| **False** | {m_fg['matrix_4class']['False']['True']} | **{m_fg['matrix_4class']['False']['False']}** | {m_fg['matrix_4class']['False']['Unsupported']} | {m_fg['matrix_4class']['False']['Unverifiable']} | {sum(m_fg['matrix_4class']['False'].values())} |
| **Unsupported** | {m_fg['matrix_4class']['Unsupported']['True']} | {m_fg['matrix_4class']['Unsupported']['False']} | **{m_fg['matrix_4class']['Unsupported']['Unsupported']}** | {m_fg['matrix_4class']['Unsupported']['Unverifiable']} | {sum(m_fg['matrix_4class']['Unsupported'].values())} |
| **Unverifiable** | {m_fg['matrix_4class']['Unverifiable']['True']} | {m_fg['matrix_4class']['Unverifiable']['False']} | {m_fg['matrix_4class']['Unverifiable']['Unsupported']} | **{m_fg['matrix_4class']['Unverifiable']['Unverifiable']}** | {sum(m_fg['matrix_4class']['Unverifiable'].values())} |

### Raw Web Search Baseline
| Ground Truth \\ Predicted | True | False | Unsupported | Unverifiable | Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True** | **{m_raw['matrix_4class']['True']['True']}** | {m_raw['matrix_4class']['True']['False']} | {m_raw['matrix_4class']['True']['Unsupported']} | {m_raw['matrix_4class']['True']['Unverifiable']} | {sum(m_raw['matrix_4class']['True'].values())} |
| **False** | {m_raw['matrix_4class']['False']['True']} | **{m_raw['matrix_4class']['False']['False']}** | {m_raw['matrix_4class']['False']['Unsupported']} | {m_raw['matrix_4class']['False']['Unverifiable']} | {sum(m_raw['matrix_4class']['False'].values())} |
| **Unsupported** | {m_raw['matrix_4class']['Unsupported']['True']} | {m_raw['matrix_4class']['Unsupported']['False']} | **{m_raw['matrix_4class']['Unsupported']['Unsupported']}** | {m_raw['matrix_4class']['Unsupported']['Unverifiable']} | {sum(m_raw['matrix_4class']['Unsupported'].values())} |
| **Unverifiable** | {m_raw['matrix_4class']['Unverifiable']['True']} | {m_raw['matrix_4class']['Unverifiable']['False']} | {m_raw['matrix_4class']['Unverifiable']['Unsupported']} | **{m_raw['matrix_4class']['Unverifiable']['Unverifiable']}** | {sum(m_raw['matrix_4class']['Unverifiable'].values())} |

### Fair Ungrounded Zero-Shot Baseline
| Ground Truth \\ Predicted | True | False | Unsupported | Unverifiable | Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True** | **{m_zs['matrix_4class']['True']['True']}** | {m_zs['matrix_4class']['True']['False']} | {m_zs['matrix_4class']['True']['Unsupported']} | {m_zs['matrix_4class']['True']['Unverifiable']} | {sum(m_zs['matrix_4class']['True'].values())} |
| **False** | {m_zs['matrix_4class']['False']['True']} | **{m_zs['matrix_4class']['False']['False']}** | {m_zs['matrix_4class']['False']['Unsupported']} | {m_zs['matrix_4class']['False']['Unverifiable']} | {sum(m_zs['matrix_4class']['False'].values())} |
| **Unsupported** | {m_zs['matrix_4class']['Unsupported']['True']} | {m_zs['matrix_4class']['Unsupported']['False']} | **{m_zs['matrix_4class']['Unsupported']['Unsupported']}** | {m_zs['matrix_4class']['Unsupported']['Unverifiable']} | {sum(m_zs['matrix_4class']['Unsupported'].values())} |
| **Unverifiable** | {m_zs['matrix_4class']['Unverifiable']['True']} | {m_zs['matrix_4class']['Unverifiable']['False']} | {m_zs['matrix_4class']['Unverifiable']['Unsupported']} | **{m_zs['matrix_4class']['Unverifiable']['Unverifiable']}** | {sum(m_zs['matrix_4class']['Unverifiable'].values())} |

---

## 4. Per-Claim Evaluation Auditing (First 100 Claims)

| ID | Domain | Expected | FactGuard | Raw Search | Zero-Shot | Claim Excerpt |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
"""
    for r in records[:100]:
        cid = r["id"]
        dom = r.get("domain", "General")[:15]
        exp = r["expected"]
        fg_v = r["factguard"]["verdict"]
        raw_v = r["raw_search"]["verdict"]
        zs_v = r["zero_shot"]["verdict"]

        fg_icon = "✅" if fg_v == exp else "❌"
        raw_icon = "✅" if raw_v == exp else "❌"
        zs_icon = "✅" if zs_v == exp else "❌"

        excerpt = r["claim"].replace("\n", " ")[:60]
        md += f"| `{cid}` | {dom} | `{exp}` | {fg_icon} {fg_v} | {raw_icon} {raw_v} | {zs_icon} {zs_v} | {excerpt}... |\n"

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Generated formal report at {report_path}.")


def main():
    results_path = os.path.join(root_dir, "tests", "data", "heldout_suite", "eval_results_heldout_300.json")
    frozen_path = os.path.join(root_dir, "tests", "data", "heldout_suite", "frozen_evidence_heldout_300.json")
    report_path = os.path.join(root_dir, "tests", "data", "heldout_suite", "report_heldout_300.md")

    with open(results_path, "r", encoding="utf-8") as f:
        telemetry = json.load(f)

    with open(frozen_path, "r", encoding="utf-8") as f:
        frozen_evidence = json.load(f)

    records = telemetry["per_claim_records"]
    affected_indices = []

    for idx, r in enumerate(records):
        has_fail = any("LLM verification unavailable" in r[s].get("reasoning", "") for s in ["factguard", "raw_search", "zero_shot"])
        if has_fail:
            affected_indices.append(idx)

    print(f"Found {len(affected_indices)} affected claims out of {len(records)}.")

    for count, idx in enumerate(affected_indices, 1):
        r = records[idx]
        cid = r["id"]
        claim_text = r["claim"]
        expected = r["expected"]
        ev = frozen_evidence.get(cid, [])

        print(f"\n[{count}/{len(affected_indices)}] Re-evaluating {cid} [{expected}]: {claim_text[:65]}...")

        # FactGuard
        if "LLM verification unavailable" in r["factguard"].get("reasoning", ""):
            print("  -> Re-running FactGuard...")
            fg_res = evaluate_factguard_safe(claim_text, ev)
            fg_icon = "✅" if fg_res["verdict"] == expected else "❌"
            print(f"     FG: {fg_icon} {fg_res['verdict']} (conf: {fg_res['confidence']:.2f})")
            r["factguard"] = fg_res
            time.sleep(1.0)

        # Raw Search
        if "LLM verification unavailable" in r["raw_search"].get("reasoning", ""):
            print("  -> Re-running Raw Search...")
            raw_res = evaluate_raw_search_safe(claim_text, ev)
            raw_icon = "✅" if raw_res["verdict"] == expected else "❌"
            print(f"     Raw: {raw_icon} {raw_res['verdict']} (conf: {raw_res['confidence']:.2f})")
            r["raw_search"] = raw_res
            time.sleep(1.0)

        # Zero-Shot
        if "LLM verification unavailable" in r["zero_shot"].get("reasoning", ""):
            print("  -> Re-running Zero-Shot...")
            zs_res = evaluate_zero_shot_safe(claim_text)
            zs_icon = "✅" if zs_res["verdict"] == expected else "❌"
            print(f"     ZS: {zs_icon} {zs_res['verdict']} (conf: {zs_res['confidence']:.2f})")
            r["zero_shot"] = zs_res
            time.sleep(1.0)

        records[idx] = r

        # Intermediate save every 5 claims
        if count % 5 == 0:
            telemetry["per_claim_records"] = records
            with open(results_path, "w", encoding="utf-8") as f:
                json.dump(telemetry, f, indent=2)

    # Recompute metrics
    fg_items = [{"verdict": r["factguard"]["verdict"], "expected": r["expected"]} for r in records]
    raw_items = [{"verdict": r["raw_search"]["verdict"], "expected": r["expected"]} for r in records]
    zs_items = [{"verdict": r["zero_shot"]["verdict"], "expected": r["expected"]} for r in records]

    m_fg = compute_system_metrics(fg_items)
    m_raw = compute_system_metrics(raw_items)
    m_zs = compute_system_metrics(zs_items)

    mc_raw = compute_mcnemar(fg_items, raw_items)
    mc_zs = compute_mcnemar(fg_items, zs_items)

    telemetry["metadata"]["timestamp_re_eval"] = time.time()
    telemetry["systems"] = {
        "factguard": m_fg,
        "raw_search": m_raw,
        "fair_zero_shot": m_zs
    }
    telemetry["paired_comparisons"] = {
        "factguard_vs_raw_search": mc_raw,
        "factguard_vs_zero_shot": mc_zs
    }
    telemetry["per_claim_records"] = records

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2)
    print(f"\nSaved updated telemetry to {results_path}.")

    generate_markdown_report(report_path, len(records), m_fg, m_raw, m_zs, mc_raw, mc_zs, records)

    print("\n" + "=" * 60)
    print("RE-EVALUATION SUMMARY:")
    print(f"FactGuard AI: {m_fg['correct_4class']}/300 ({m_fg['accuracy_4class']*100:.1f}%) | 3-Class: {m_fg['accuracy_3class']*100:.1f}%")
    print(f"Raw Search:   {m_raw['correct_4class']}/300 ({m_raw['accuracy_4class']*100:.1f}%) | 3-Class: {m_raw['accuracy_3class']*100:.1f}%")
    print(f"Zero-Shot:    {m_zs['correct_4class']}/300 ({m_zs['accuracy_4class']*100:.1f}%) | 3-Class: {m_zs['accuracy_3class']*100:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    main()
