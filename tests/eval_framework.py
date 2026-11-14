# tests/eval_framework.py
"""
FactGuard AI - Scientific Evaluation & Peer-Review Benchmark Framework
Implements:
1. 3-Way Confusion Matrix (True / False / Unverifiable)
2. Coverage, Selective Accuracy, Macro-F1, and Discordant Error Breakdowns
3. Wilson Score 95% Confidence Intervals
4. McNemar's Paired Statistical Significance Test against baselines
5. Baselines: Ungrounded LLM, Raw Search + LLM, and FactGuard AI
6. Component Ablation Runner (No SpaCy, No Domain Trust, No BM25, Wikipedia-only, DDG-only)
7. Frozen Evidence Caching for zero-drift reproducibility
"""

import sys
import os
import json
import time
import math
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(backend_dir))

from core.claim_extractor import claim_extractor
from core.web_search import web_search
from core.re_ranker import re_ranker
from core.domain_trust import get_domain_trust
from core.llm_service import llm_service, Verdict
from config import TOP_K_RETRIEVE, TOP_K_RERANK_RESULTS

DATA_DIR = Path(__file__).resolve().parent / "data"
FROZEN_EVIDENCE_PATH = DATA_DIR / "frozen_evidence.json"


# --- Statistical Helpers ---

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


def compute_mcnemar_test(b: int, c: int) -> Tuple[float, float]:
    """
    Compute McNemar's test with continuity correction.
    b = Model A correct, Model B wrong
    c = Model A wrong, Model B correct
    Returns (chi2_statistic, p_value_approx)
    """
    total = b + c
    if total == 0:
        return 0.0, 1.0
    
    chi2 = (abs(b - c) - 1.0) ** 2 / total
    # Approximate p-value from 1-degree of freedom Chi-Square distribution
    # Using complementary error function approximation
    p_val = math.erfc(math.sqrt(chi2) / math.sqrt(2))
    return chi2, max(0.0, min(1.0, p_val))


# --- Frozen Evidence Cache ---

def load_or_fetch_frozen_evidence(claims: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Load or fetch live evidence once and freeze to disk for zero-drift benchmark runs."""
    evidence_cache: Dict[str, List[Dict[str, Any]]] = {}
    if FROZEN_EVIDENCE_PATH.exists():
        try:
            with open(FROZEN_EVIDENCE_PATH, "r", encoding="utf-8") as f:
                evidence_cache = json.load(f)
        except Exception as e:
            print(f"Warning loading frozen evidence: {e}")

    updated = False
    for item in claims:
        cid = item.get("id") or item["claim"]
        if cid not in evidence_cache:
            claim_text = item["claim"]
            extracted = claim_extractor.extract(claim_text)
            results = web_search.search(extracted, max_results=TOP_K_RETRIEVE)
            evidence_cache[cid] = results
            updated = True

    if updated:
        FROZEN_EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(FROZEN_EVIDENCE_PATH, "w", encoding="utf-8") as f:
            json.dump(evidence_cache, f, indent=2)

    return evidence_cache


# --- Evaluation Engine ---

class EvalEngine:
    def __init__(self, use_frozen: bool = True):
        self.use_frozen = use_frozen

    def evaluate_claim(
        self,
        claim_dict: Dict[str, Any],
        config: str = "factguard_full",
        frozen_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single claim under a specified configuration:
        - 'factguard_full': Standard pipeline (SpaCy + Live RAG + BM25Okapi + Domain Trust)
        - 'baseline_ungrounded': Zero-shot LLM with no search
        - 'baseline_raw_ddg': Raw search query + raw top snippets (no extraction, no re-ranking, no domain trust)
        - 'ablation_no_spacy': Raw claim used for search without SpaCy proposition extraction
        - 'ablation_no_domain_trust': BM25Okapi without domain multiplier
        - 'ablation_no_rerank': Raw search order directly to LLM
        - 'ablation_wikipedia_only': Only Wikipedia sources
        - 'ablation_ddg_only': Only DuckDuckGo sources
        """
        raw_text = claim_dict["claim"]
        cid = claim_dict.get("id") or raw_text
        start_t = time.time()

        # 1. Baseline: Zero-shot Ungrounded LLM
        if config == "baseline_ungrounded":
            prompt = (
                f"Fact-check the following claim based purely on your internal parameters.\n"
                f"Choose exactly one verdict: 'True', 'False', or 'Unverifiable'.\n"
                f"Claim: \"{raw_text}\"\n\n"
                f"Respond with JSON: {{\"verdict\": \"True\"|\"False\"|\"Unverifiable\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\"}}"
            )
            try:
                res_verdict = llm_service.get_verdict(raw_text, evidence=[], provider="groq")
                v = res_verdict.verdict
                c = res_verdict.confidence
                r = res_verdict.reasoning
            except Exception as e:
                v, c, r = "Unverifiable", 0.0, str(e)
            return {"verdict": v, "confidence": c, "reasoning": r, "latency": time.time() - start_t}

        # 2. Extract Claim (or skip in ablation)
        if config in ("baseline_raw_ddg", "ablation_no_spacy"):
            search_query = raw_text
        else:
            search_query = claim_extractor.extract(raw_text)

        # 3. Retrieve Evidence
        if frozen_results is not None:
            raw_evidence = list(frozen_results)
        else:
            raw_evidence = web_search.search(search_query, max_results=TOP_K_RETRIEVE)

        # Source-specific ablations
        if config == "ablation_wikipedia_only":
            raw_evidence = [e for e in raw_evidence if "wikipedia" in e.get("source", "").lower() or "wikipedia.org" in e.get("url", "").lower()]
        elif config == "ablation_ddg_only":
            raw_evidence = [e for e in raw_evidence if "wikipedia" not in e.get("source", "").lower() and "wikipedia.org" not in e.get("url", "").lower()]

        # 4. Re-rank Evidence
        if config in ("baseline_raw_ddg", "ablation_no_rerank"):
            # Raw retrieval order without BM25 or domain trust
            selected_items = [(item, 1.0) for item in raw_evidence[:TOP_K_RERANK_RESULTS]]
        elif config == "ablation_no_domain_trust":
            # BM25 without domain trust multiplier
            selected_items = []
            if raw_evidence:
                doc_texts = [f"{item.get('title', '')}: {item.get('snippet', '')}" for item in raw_evidence]
                scores = re_ranker._compute_bm25_scores(search_query, doc_texts)
                paired = sorted(zip(raw_evidence, scores), key=lambda x: x[1], reverse=True)[:TOP_K_RERANK_RESULTS]
                selected_items = paired
        else:
            # Full FactGuard: BM25Okapi + Domain Trust Matrix
            selected_items = re_ranker.rerank_items(search_query, raw_evidence, top_k=TOP_K_RERANK_RESULTS)

        # Format evidence items
        evidence_items = []
        for item, _ in selected_items:
            title = item.get("title", "Web")
            snippet = item.get("snippet", "")
            trust = item.get("domain_trust", {})
            badge = trust.get("badge", item.get("source", "Web"))
            if trust.get("is_satire"):
                evidence_items.append(f"[{title} | ⚠️ SATIRE SOURCE] {snippet}")
            else:
                evidence_items.append(f"[{title} | {badge}] {snippet}")

        # 5. LLM Synthesis
        try:
            verdict_obj = llm_service.get_verdict(
                claim=search_query,
                evidence=evidence_items,
                provider="groq"
            )
            v = verdict_obj.verdict
            c = verdict_obj.confidence
            r = verdict_obj.reasoning
        except Exception as e:
            v, c, r = "Unverifiable", 0.0, str(e)

        return {
            "verdict": v,
            "confidence": c,
            "reasoning": r,
            "evidence_count": len(evidence_items),
            "latency": time.time() - start_t
        }

    def run_benchmark_suite(
        self,
        claims: List[Dict[str, Any]],
        configs: List[str] = ["baseline_ungrounded", "baseline_raw_ddg", "factguard_full"]
    ) -> Dict[str, Any]:
        """Run benchmark on claims across all requested configurations."""
        evidence_map = load_or_fetch_frozen_evidence(claims) if self.use_frozen else {}
        results_by_config: Dict[str, List[Dict[str, Any]]] = {cfg: [] for cfg in configs}

        print(f"\n🚀 Running Evaluation on {len(claims)} claims across {len(configs)} configurations...")
        for i, item in enumerate(claims, 1):
            cid = item.get("id") or item["claim"]
            expected = item["expected"]
            frozen_ev = evidence_map.get(cid)

            for cfg in configs:
                res = self.evaluate_claim(item, config=cfg, frozen_results=frozen_ev)
                res["expected"] = expected
                res["claim"] = item["claim"]
                res["id"] = item.get("id", f"C{i}")
                res["domain"] = item.get("domain", "General")
                res["is_correct"] = (res["verdict"] == expected)
                results_by_config[cfg].append(res)

        return results_by_config


def compute_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute 3x3 confusion matrix, coverage, selective accuracy, and Wilson CIs."""
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

    # Macro F1
    f1_scores = []
    for c in classes:
        tp = cm[c][c]
        fp = sum(cm[other][c] for other in classes if other != c)
        fn = sum(cm[c][other] for other in classes if other != c)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        f1_scores.append(f1)
    macro_f1 = sum(f1_scores) / len(f1_scores)

    # Latencies
    latencies = [r.get("latency", 0.0) for r in results]
    latencies.sort()
    p50 = latencies[len(latencies) // 2] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "accuracy_ci_95": (acc_ci_low, acc_ci_high),
        "coverage": coverage,
        "selective_accuracy": selective_acc,
        "macro_f1": macro_f1,
        "confusion_matrix": cm,
        "p50_latency": p50,
        "p95_latency": p95,
        "false_positives": cm["False"]["True"],
        "false_negatives": cm["True"]["False"],
        "unverifiable_abstentions": sum(cm[c]["Unverifiable"] for c in classes)
    }
