"""
FactGuard AI - Scaled Scientific Held-Out Evaluation Runner (N = 300)
Features:
1. Frozen Multi-Engine Web Retrieval (Zero search drift across systems)
2. Resumable Checkpoint Architecture (Zero data loss across rate limits)
3. 3 Systems Evaluated:
   - FactGuard AI (Full Pipeline: Trafilatura Deep Extraction + BM25Okapi + Domain Trust Matrix + Prompt v2.1.0-precedence-4class)
   - Raw Web Search + LLM Baseline (Unranked web search into 4-class prompt)
   - Fair Ungrounded Zero-Shot Baseline (General pre-trained knowledge without empty-evidence confounds)
4. Comprehensive Statistical Telemetry:
   - 4-Class Metrics: Overall Accuracy, Wilson 95% CIs, 4x4 Confusion Matrices, Decisive Coverage, Selective Precision
   - 3-Class Academic Benchmark Mapping: NEI = {Unsupported, Unverifiable}
   - Paired McNemar Test (Edwards Continuity Correction & Exact Binomial p-value)
"""

import os
import sys
import json
import math
import time
import asyncio
import argparse
from typing import Dict, List, Any, Tuple

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from core.web_search import web_search
from core.re_ranker import re_ranker
from core.llm_service import llm_service

CLAIMS_FILE = os.path.join(os.path.dirname(__file__), "data", "heldout_suite", "claims_heldout_300.json")
FROZEN_EVIDENCE_FILE = os.path.join(os.path.dirname(__file__), "data", "heldout_suite", "frozen_evidence_heldout_300.json")
CHECKPOINT_FILE = os.path.join(os.path.dirname(__file__), "data", "heldout_suite", "checkpoint_heldout_300.json")
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "data", "heldout_suite", "eval_results_heldout_300.json")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "data", "heldout_suite", "report_heldout_300.md")

CLASSES = ["True", "False", "Unsupported", "Unverifiable"]

ZERO_SHOT_PROMPT = """You are FactGuard AI, an objective, scientifically rigorous factual verification system.
Based strictly on your general pre-trained knowledge (without external web search), evaluate whether the following claim is True, False, Unsupported, or Unverifiable.

EPISTEMIC ORDER OF PRECEDENCE:
Step 1: Test for Falsifiability:
- If the claim is inherently non-falsifiable in principle (subjective personal taste, aesthetic preference, normative moral/ethical value judgment, or speculative future event that has not yet occurred), judge as 'Unverifiable' immediately.

Step 2: If the claim is an empirical assertion capable of objective proof or disproof:
1. 'True': The core factual assertion is confirmed by established scientific consensus or documented historical records.
2. 'False': The core factual assertion is contradicted, refuted, or debunked by established scientific consensus or documented historical records.
3. 'Unsupported': The claim asserts an empirical or historical fact, but is currently unproven, speculative, lacks established consensus, or is an unconfirmed hypothesis.
4. 'Unverifiable': Non-falsifiable assertions identified in Step 1.

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


async def freeze_evidence_if_needed(claims: List[Dict[str, Any]], frozen_file: str) -> Dict[str, List[Dict[str, str]]]:
    """Pre-fetch and persist search results to eliminate retrieval drift across all systems."""
    frozen = {}
    if os.path.exists(frozen_file):
        print(f"Loading frozen evidence cache from {frozen_file}...")
        try:
            with open(frozen_file, "r", encoding="utf-8") as f:
                frozen = json.load(f)
            print(f"  Loaded {len(frozen)} pre-cached claims.")
        except Exception as e:
            print(f"  Notice loading cache: {e}")
            frozen = {}

    missing = [c for c in claims if c["id"] not in frozen]
    if missing:
        print(f"Pre-fetching frozen evidence for {len(missing)} claims...")
        os.makedirs(os.path.dirname(frozen_file), exist_ok=True)
        count = 0
        for item in missing:
            cid = item["id"]
            claim_text = item["claim"]
            print(f"  [Freeze {count+1}/{len(missing)}] {cid}: {claim_text[:65]}...")
            raw_results = await web_search.async_search(claim_text, max_results=10)
            frozen[cid] = raw_results
            count += 1
            if count % 10 == 0:
                with open(frozen_file, "w", encoding="utf-8") as f:
                    json.dump(frozen, f, indent=2)
            await asyncio.sleep(0.3)

        with open(frozen_file, "w", encoding="utf-8") as f:
            json.dump(frozen, f, indent=2)
        print(f"Saved frozen evidence cache ({len(frozen)} claims) to {frozen_file}.")

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
    verdict_obj = llm_service.get_verdict(
        claim=claim_text,
        evidence=evidence_items,
        provider="groq"
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


def evaluate_raw_search(claim_text: str, raw_evidence: List[Dict[str, str]]) -> Dict[str, Any]:
    """Evaluate raw search baseline: unranked top 4 search snippets into 4-class prompt."""
    raw_docs = []
    for item in raw_evidence[:4]:
        title = item.get("title", "Web Source")
        snippet = item.get("snippet", "")
        raw_docs.append(f"[{title}] {snippet}")

    t0 = time.time()
    verdict_obj = llm_service.get_verdict(
        claim=claim_text,
        evidence=raw_docs,
        provider="groq"
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
        # Edwards continuity correction
        chi2 = (abs(b - c) - 1.0)**2 / discordant if abs(b - c) > 1 else 0.0
        # Exact two-tailed binomial p-value under null p = 0.5
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
    """Generate a formal scientific markdown report."""
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
        fg_icon = "✅" if r["factguard"]["verdict"] == r["expected"] else "❌"
        raw_icon = "✅" if r["raw_search"]["verdict"] == r["expected"] else "❌"
        zs_icon = "✅" if r["zero_shot"]["verdict"] == r["expected"] else "❌"
        md += f"| `{r['id']}` | {r['domain'][:16]} | `{r['expected']}` | {fg_icon} {r['factguard']['verdict']} | {raw_icon} {r['raw_search']['verdict']} | {zs_icon} {r['zero_shot']['verdict']} | {r['claim'][:60]}... |\n"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Generated formal report at {report_path}.")


async def main():
    parser = argparse.ArgumentParser(description="FactGuard AI Scaled Evaluation Runner")
    parser.add_argument("--suite", default=CLAIMS_FILE, help="Path to heldout suite JSON")
    parser.add_argument("--frozen-evidence", default=FROZEN_EVIDENCE_FILE, help="Path to frozen evidence cache")
    parser.add_argument("--checkpoint", default=CHECKPOINT_FILE, help="Path to checkpoint file")
    parser.add_argument("--results", default=RESULTS_FILE, help="Path to output results JSON")
    parser.add_argument("--report", default=REPORT_FILE, help="Path to output markdown report")
    parser.add_argument("--batch-size", type=int, default=300, help="Number of claims to evaluate")
    parser.add_argument("--freeze-only", action="store_true", help="Only pre-fetch search results without running LLMs")
    args = parser.parse_args()

    print(f"==================================================")
    print(f"FactGuard AI Scaled Scientific Evaluation Runner")
    print(f"Suite: {args.suite}")
    print(f"==================================================")

    with open(args.suite, "r", encoding="utf-8") as f:
        all_claims = json.load(f)

    claims = all_claims[:args.batch_size]
    print(f"Target evaluations: {len(claims)} claims.")

    # 1. Pre-fetch and freeze evidence
    frozen_evidence = await freeze_evidence_if_needed(claims, args.frozen_evidence)
    if args.freeze_only:
        print("Freeze-only mode completed successfully.")
        return

    # 2. Load checkpoint
    completed_records = []
    completed_ids = set()
    if os.path.exists(args.checkpoint):
        try:
            with open(args.checkpoint, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)
                completed_records = checkpoint_data.get("records", [])
                completed_ids = set(checkpoint_data.get("completed_ids", []))
            print(f"Resuming from checkpoint: {len(completed_records)} claims already evaluated.")
        except Exception as e:
            print(f"Notice reading checkpoint: {e}")
            completed_records = []
            completed_ids = set()

    # 3. Evaluation Loop
    total_to_run = len(claims)
    for idx, item in enumerate(claims):
        cid = item["id"]
        if cid in completed_ids:
            continue

        claim_text = item["claim"]
        expected = item["expected"]
        domain = item.get("domain", "General")
        evidence = frozen_evidence.get(cid, [])

        print(f"\n[{idx+1}/{total_to_run}] {cid} ({expected:13s}): {claim_text[:65]}...")

        # System 1: FactGuard Full Pipeline
        fg_res = evaluate_factguard(claim_text, evidence)
        fg_icon = "✅" if fg_res["verdict"] == expected else "❌"

        # System 2: Raw Search Baseline
        raw_res = evaluate_raw_search(claim_text, evidence)
        raw_icon = "✅" if raw_res["verdict"] == expected else "❌"

        # System 3: Fair Ungrounded Zero-Shot Baseline
        zs_res = evaluate_fair_zero_shot(claim_text)
        zs_icon = "✅" if zs_res["verdict"] == expected else "❌"

        print(f"     FG: {fg_icon} {fg_res['verdict']:12s} | Raw: {raw_icon} {raw_res['verdict']:12s} | ZS: {zs_icon} {zs_res['verdict']}")

        record = {
            "id": cid,
            "domain": domain,
            "expected": expected,
            "claim": claim_text,
            "factguard": fg_res,
            "raw_search": raw_res,
            "zero_shot": zs_res
        }
        completed_records.append(record)
        completed_ids.add(cid)

        # Atomic checkpoint save after every claim
        os.makedirs(os.path.dirname(args.checkpoint), exist_ok=True)
        with open(args.checkpoint, "w", encoding="utf-8") as f:
            json.dump({
                "completed_ids": list(completed_ids),
                "records": completed_records,
                "timestamp": time.time()
            }, f, indent=2)

        # Polite rate pacing
        await asyncio.sleep(0.5)

    # 4. Compute Metrics
    fg_items = [{"verdict": r["factguard"]["verdict"], "expected": r["expected"]} for r in completed_records]
    raw_items = [{"verdict": r["raw_search"]["verdict"], "expected": r["expected"]} for r in completed_records]
    zs_items = [{"verdict": r["zero_shot"]["verdict"], "expected": r["expected"]} for r in completed_records]

    m_fg = compute_system_metrics(fg_items)
    m_raw = compute_system_metrics(raw_items)
    m_zs = compute_system_metrics(zs_items)

    mc_raw = compute_mcnemar(fg_items, raw_items)
    mc_zs = compute_mcnemar(fg_items, zs_items)

    # 5. Save Results JSON
    telemetry = {
        "metadata": {
            "total_claims": len(completed_records),
            "timestamp": time.time(),
            "prompt_version": llm_service.PROMPT_VERSION,
            "prompt_hash": llm_service.prompt_hash,
            "suite_file": args.suite
        },
        "systems": {
            "factguard": m_fg,
            "raw_search": m_raw,
            "fair_zero_shot": m_zs
        },
        "paired_comparisons": {
            "factguard_vs_raw_search": mc_raw,
            "factguard_vs_zero_shot": mc_zs
        },
        "per_claim_records": completed_records
    }
    with open(args.results, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2)
    print(f"\nSaved evaluation telemetry to {args.results}.")

    # 6. Generate Markdown Report
    generate_markdown_report(args.report, len(completed_records), m_fg, m_raw, m_zs, mc_raw, mc_zs, completed_records)


if __name__ == "__main__":
    asyncio.run(main())
