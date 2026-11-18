"""
FactGuard AI - Held-Out Pilot Scientific Evaluation Runner (N = 32)
Features:
1. Frozen Multi-Engine Web Retrieval (Zero search drift across systems)
2. 3 Systems Evaluated:
   - FactGuard AI (Full Pipeline: BM25Okapi + Domain Trust Matrix + Prompt v2.0.0-clean-4class)
   - Raw Web Search + LLM Baseline (Unranked web search into 4-class prompt)
   - Fair Ungrounded Zero-Shot Baseline (Parametric knowledge without empty-evidence confound)
3. 4-Class Metrics: Overall Accuracy, Wilson 95% CIs, 4x4 Confusion Matrices, Selective Precision
4. 3-Class Academic Benchmark Mapping: NEI = {Unsupported, Unverifiable}
5. Exact Paired McNemar Test (Discordant binomial test)
"""

import os
import sys
import json
import math
import time
import asyncio
from typing import Dict, List, Any, Tuple

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from core.web_search import web_search
from core.re_ranker import re_ranker
from core.llm_service import llm_service

CLAIMS_FILE = os.path.join(os.path.dirname(__file__), "data", "heldout_suite", "claims_heldout_pilot.json")
FROZEN_EVIDENCE_FILE = os.path.join(os.path.dirname(__file__), "data", "heldout_suite", "frozen_evidence_heldout_pilot.json")
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "data", "heldout_suite", "eval_results_heldout_pilot.json")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "data", "heldout_suite", "report_heldout_pilot.md")

CLASSES = ["True", "False", "Unsupported", "Unverifiable"]

ZERO_SHOT_PROMPT = """You are FactGuard AI, an objective, scientifically rigorous factual verification system.
Based strictly on your general pre-trained knowledge (without external web search), evaluate whether the following claim is True, False, Unsupported, or Unverifiable.

CORE VERDICT RULES:
1. 'True': The core factual assertion is confirmed by established scientific consensus or authoritative historical records.
2. 'False': The core factual assertion is contradicted, refuted, or debunked by established scientific consensus or documented historical records.
3. 'Unsupported': The claim asserts an empirical or historical fact, but is currently unproven, speculative, lacks established consensus, or is an unconfirmed hypothesis.
4. 'Unverifiable': The claim is fundamentally non-falsifiable in principle: subjective personal taste, aesthetic preference, ethical opinion, or speculative future prediction.

CLAIM: {claim}

Return valid JSON with these fields:
{{
  "verdict": "True" | "False" | "Unsupported" | "Unverifiable",
  "confidence": 0.0 to 1.0,
  "reasoning": "Clear 1-3 sentence factual explanation based strictly on general knowledge",
  "consensus_score": 0.0 to 1.0,
  "disputed": false,
  "numerical_variance": null
}}"""


def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculate Wilson score interval for binomial proportions."""
    if total == 0:
        return 0.0, 0.0
    z = 1.95996  # 95% confidence
    p = successes / total
    denominator = 1 + z**2 / total
    centre_adjusted_probability = p + z**2 / (2 * total)
    adjusted_std_dev = math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)
    lower = (centre_adjusted_probability - z * adjusted_std_dev) / denominator
    upper = (centre_adjusted_probability + z * adjusted_std_dev) / denominator
    return max(0.0, lower), min(1.0, upper)


async def freeze_evidence_if_needed(claims: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
    """Pre-fetch and persist search results to eliminate retrieval drift."""
    frozen = {}
    if os.path.exists(FROZEN_EVIDENCE_FILE):
        print(f"Loading frozen evidence cache from {FROZEN_EVIDENCE_FILE}...")
        try:
            with open(FROZEN_EVIDENCE_FILE, "r", encoding="utf-8") as f:
                frozen = json.load(f)
        except Exception:
            frozen = {}

    updated = False
    for item in claims:
        cid = item["id"]
        claim_text = item["claim"]
        if cid not in frozen:
            print(f"  [Freeze] Searching evidence for {cid}: {claim_text[:60]}...")
            raw_results = await web_search.async_search(claim_text, max_results=12)
            frozen[cid] = raw_results
            updated = True
            await asyncio.sleep(0.5)

    if updated:
        os.makedirs(os.path.dirname(FROZEN_EVIDENCE_FILE), exist_ok=True)
        with open(FROZEN_EVIDENCE_FILE, "w", encoding="utf-8") as f:
            json.dump(frozen, f, indent=2)
        print(f"Saved frozen evidence cache ({len(frozen)} claims) to {FROZEN_EVIDENCE_FILE}.")

    return frozen


def evaluate_factguard(claim_text: str, raw_evidence: List[Dict[str, str]]) -> Dict[str, Any]:
    """Evaluate using FactGuard full pipeline: BM25 + Domain Trust + 4-class Prompt."""
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

    t0 = time.time()
    verdict_obj = llm_service.get_verdict(claim=claim_text, evidence=evidence_items, provider="groq")
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


def evaluate_raw_search(claim_text: str, raw_evidence: List[Dict[str, str]]) -> Dict[str, Any]:
    """Evaluate using Raw Web Search: Unranked snippets fed directly into 4-class prompt."""
    raw_docs = []
    for doc in raw_evidence[:5]:
        title = doc.get("title", "Web")
        text = doc.get("snippet", "")
        raw_docs.append(f"[{title}] {text}")

    t0 = time.time()
    verdict_obj = llm_service.get_verdict(claim=claim_text, evidence=raw_docs, provider="groq")
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


def evaluate_fair_zero_shot(claim_text: str) -> Dict[str, Any]:
    """
    Evaluate ungrounded zero-shot baseline using a fair prompt testing internal pre-trained memory.
    Avoids the rule-3 empty-evidence confound.
    """
    t0 = time.time()
    verdict_obj = llm_service.get_verdict(
        claim=claim_text,
        evidence=[],
        provider="groq",
        prompt_template=ZERO_SHOT_PROMPT
    )
    elapsed = time.time() - t0

    return {
        "verdict": verdict_obj.verdict,
        "confidence": verdict_obj.confidence,
        "reasoning": verdict_obj.reasoning,
        "latency_sec": elapsed,
        "model": verdict_obj.model_used
    }


def compute_system_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute 4-class and 3-class academic metrics for an evaluation set."""
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

        # Decisive coverage: True or False
        if pred in ["True", "False"]:
            decisive_total += 1
            if pred == expected:
                decisive_correct += 1

        # 3-Class FEVER mapping:
        # True -> SUPPORTS, False -> REFUTES, {Unsupported, Unverifiable} -> NEI
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
    """Compute paired McNemar test and discordant binomial exact test."""
    b = 0  # A correct, B wrong
    c = 0  # B correct, A wrong
    both_correct = 0
    both_wrong = 0

    for ra, rb in zip(results_a, results_b):
        a_corr = (ra["verdict"] == ra["expected"])
        b_corr = (rb["verdict"] == rb["expected"])

        if a_corr and b_corr:
            both_correct += 1
        elif not a_corr and not b_corr:
            both_wrong += 1
        elif a_corr and not b_corr:
            b += 1
        else:
            c += 1

    discordant = b + c
    chi2 = ((abs(b - c) - 1)**2) / discordant if discordant > 0 else 0.0

    # Exact two-sided binomial p-value for discordant pairs
    p_value = 1.0
    if discordant > 0:
        p_val_half = 0.0
        k = min(b, c)
        for i in range(k + 1):
            p_val_half += math.comb(discordant, i) * (0.5**discordant)
        p_value = min(1.0, 2 * p_val_half)

    return {
        "both_correct": both_correct,
        "both_wrong": both_wrong,
        "system_a_only": b,
        "system_b_only": c,
        "discordant_pairs": discordant,
        "chi2": chi2,
        "p_value": p_value
    }


async def main():
    print("=" * 60)
    print("FactGuard AI - Held-Out Pilot Scientific Evaluation (N = 32)")
    print("Epistemic Framework: 4-Class Taxonomy (True, False, Unsupported, Unverifiable)")
    print("=" * 60)

    with open(CLAIMS_FILE, "r", encoding="utf-8") as f:
        claims = json.load(f)

    print(f"Loaded {len(claims)} held-out pilot claims from {CLAIMS_FILE}.")

    # 1. Freeze evidence
    frozen_evidence = await freeze_evidence_if_needed(claims)

    eval_fg = []
    eval_raw = []
    eval_zs = []

    print("\n--- Starting Evaluations Across 3 Systems ---")
    for idx, item in enumerate(claims, 1):
        cid = item["id"]
        claim = item["claim"]
        exp = item["expected"]
        evidence = frozen_evidence.get(cid, [])

        print(f"[{idx:02d}/{len(claims):02d}] {cid} ({exp:13s}): {claim[:60]}...")

        # FactGuard
        fg_res = evaluate_factguard(claim, evidence)
        fg_res["id"] = cid
        fg_res["expected"] = exp
        eval_fg.append(fg_res)

        # Raw Search
        raw_res = evaluate_raw_search(claim, evidence)
        raw_res["id"] = cid
        raw_res["expected"] = exp
        eval_raw.append(raw_res)

        # Zero-Shot
        zs_res = evaluate_fair_zero_shot(claim)
        zs_res["id"] = cid
        zs_res["expected"] = exp
        eval_zs.append(zs_res)

        fg_icon = "✅" if fg_res["verdict"] == exp else "❌"
        raw_icon = "✅" if raw_res["verdict"] == exp else "❌"
        zs_icon = "✅" if zs_res["verdict"] == exp else "❌"

        print(f"     FG: {fg_icon} {fg_res['verdict']:13s} | Raw: {raw_icon} {raw_res['verdict']:13s} | ZS: {zs_icon} {zs_res['verdict']:13s}")
        await asyncio.sleep(0.4)

    # Compute System Metrics
    m_fg = compute_system_metrics(eval_fg)
    m_raw = compute_system_metrics(eval_raw)
    m_zs = compute_system_metrics(eval_zs)

    # Compute Paired Tests
    mcnemar_fg_raw = compute_mcnemar(eval_fg, eval_raw)
    mcnemar_fg_zs = compute_mcnemar(eval_fg, eval_zs)

    results_payload = {
        "metadata": {
            "evaluation_type": "Held-Out Pilot (N = 32)",
            "taxonomy": "4-Class (True, False, Unsupported, Unverifiable)",
            "benchmark_mapping": "FEVER 3-Class (SUPPORTS, REFUTES, NEI)",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_claims": len(claims)
        },
        "systems": {
            "factguard_full": m_fg,
            "raw_search_baseline": m_raw,
            "fair_zero_shot_baseline": m_zs
        },
        "paired_comparisons": {
            "factguard_vs_raw": mcnemar_fg_raw,
            "factguard_vs_zeroshot": mcnemar_fg_zs
        },
        "per_claim_records": [
            {
                "id": c["id"],
                "domain": c.get("domain", ""),
                "expected": c["expected"],
                "claim": c["claim"],
                "factguard": {"verdict": r_fg["verdict"], "confidence": r_fg["confidence"], "reasoning": r_fg["reasoning"]},
                "raw_search": {"verdict": r_raw["verdict"], "confidence": r_raw["confidence"], "reasoning": r_raw["reasoning"]},
                "zero_shot": {"verdict": r_zs["verdict"], "confidence": r_zs["confidence"], "reasoning": r_zs["reasoning"]}
            }
            for c, r_fg, r_raw, r_zs in zip(claims, eval_fg, eval_raw, eval_zs)
        ]
    }

    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)
    print(f"\nSaved evaluation telemetry to {RESULTS_FILE}.")

    # Generate Markdown Report
    generate_markdown_report(results_payload)


def generate_markdown_report(payload: Dict[str, Any]):
    """Generate formal scientific evaluation report for the held-out pilot."""
    m_fg = payload["systems"]["factguard_full"]
    m_raw = payload["systems"]["raw_search_baseline"]
    m_zs = payload["systems"]["fair_zero_shot_baseline"]
    mc_raw = payload["paired_comparisons"]["factguard_vs_raw"]
    mc_zs = payload["paired_comparisons"]["factguard_vs_zeroshot"]
    records = payload["per_claim_records"]

    md = f"""# FactGuard AI: Held-Out Pilot Scientific Evaluation Report (N = 32)

> **Evaluation Standard**: Strictly held-out, decontaminated evaluation suite ($N = 32$). All claims were decontaminated against the 564 development claims using Levenshtein distance filtering ($< 0.65$). Evaluated with **frozen multi-engine web evidence** across all systems to ensure zero retrieval drift.

---

## 1. Headline Empirical Comparison

| System Configuration | 4-Class Accuracy | 95% Wilson CI | FEVER 3-Class Accuracy | Coverage (Decisive) | Selective Precision |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **FactGuard AI (Full Pipeline)** | **{m_fg['accuracy_4class']*100:.1f}% ({m_fg['correct_4class']}/{m_fg['total']})** | [{m_fg['accuracy_4class_ci'][0]*100:.1f}%, {m_fg['accuracy_4class_ci'][1]*100:.1f}%] | **{m_fg['accuracy_3class']*100:.1f}%** | **{m_fg['coverage']*100:.1f}%** ({m_fg['decisive_count']}/{m_fg['total']}) | **{m_fg['selective_precision']*100:.1f}%** |
| Raw Web Search + LLM Baseline | {m_raw['accuracy_4class']*100:.1f}% ({m_raw['correct_4class']}/{m_raw['total']}) | [{m_raw['accuracy_4class_ci'][0]*100:.1f}%, {m_raw['accuracy_4class_ci'][1]*100:.1f}%] | {m_raw['accuracy_3class']*100:.1f}% | {m_raw['coverage']*100:.1f}% ({m_raw['decisive_count']}/{m_raw['total']}) | {m_raw['selective_precision']*100:.1f}% |
| Fair Ungrounded Zero-Shot LLM | {m_zs['accuracy_4class']*100:.1f}% ({m_zs['correct_4class']}/{m_zs['total']}) | [{m_zs['accuracy_4class_ci'][0]*100:.1f}%, {m_zs['accuracy_4class_ci'][1]*100:.1f}%] | {m_zs['accuracy_3class']*100:.1f}% | {m_zs['coverage']*100:.1f}% ({m_zs['decisive_count']}/{m_zs['total']}) | {m_zs['selective_precision']*100:.1f}% |

---

## 2. Statistical Significance (Paired Tests)

* **FactGuard AI vs. Raw Web Search Baseline**:
  - Both Correct: `{mc_raw['both_correct']}`
  - Both Wrong: `{mc_raw['both_wrong']}`
  - FactGuard Only: `{mc_raw['system_a_only']}`
  - Raw Search Only: `{mc_raw['system_b_only']}`
  - Discordant Pairs: `{mc_raw['discordant_pairs']}`
  - McNemar Statistic ($\chi^2$): `{mc_raw['chi2']:.3f}`
  - Exact Binomial p-value: **p = {mc_raw['p_value']:.4f}**

* **FactGuard AI vs. Fair Ungrounded Zero-Shot Baseline**:
  - Both Correct: `{mc_zs['both_correct']}`
  - Both Wrong: `{mc_zs['both_wrong']}`
  - FactGuard Only: `{mc_zs['system_a_only']}`
  - Zero-Shot Only: `{mc_zs['system_b_only']}`
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

## 4. Per-Claim Evaluation Auditing

| ID | Domain | Expected | FactGuard | Raw Search | Zero-Shot | Claim Excerpt |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
"""
    for r in records:
        fg_icon = "✅" if r["factguard"]["verdict"] == r["expected"] else "❌"
        raw_icon = "✅" if r["raw_search"]["verdict"] == r["expected"] else "❌"
        zs_icon = "✅" if r["zero_shot"]["verdict"] == r["expected"] else "❌"
        md += f"| `{r['id']}` | {r['domain'][:16]} | `{r['expected']}` | {fg_icon} {r['factguard']['verdict']} | {raw_icon} {r['raw_search']['verdict']} | {zs_icon} {r['zero_shot']['verdict']} | {r['claim'][:60]}... |\n"

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Generated formal report at {REPORT_FILE}.")


if __name__ == "__main__":
    asyncio.run(main())
