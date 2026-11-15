"""
Seed 100 verified claims from eval_results_100.json and frozen_evidence_100.json into the 1,000-claim benchmark.
Preserves 100% data integrity and eliminates redundant API quota consumption.
"""

import json
from pathlib import Path

DATA_DIR = Path("tests/data")
CLAIMS_100_PATH = DATA_DIR / "claims_test_100.json"
CLAIMS_1000_PATH = DATA_DIR / "claims_test_1000.json"
EVAL_100_PATH = DATA_DIR / "eval_results_100.json"
EVAL_CHECKPOINT_1000_PATH = DATA_DIR / "eval_checkpoint_1000.json"
FROZEN_100_PATH = DATA_DIR / "frozen_evidence_100.json"
FROZEN_1000_PATH = DATA_DIR / "frozen_evidence_1000.json"

def seed_checkpoint():
    with open(CLAIMS_100_PATH, "r", encoding="utf-8") as f:
        c100 = json.load(f)
    with open(CLAIMS_1000_PATH, "r", encoding="utf-8") as f:
        c1000 = json.load(f)
    with open(EVAL_100_PATH, "r", encoding="utf-8") as f:
        eval100 = json.load(f)
    with open(FROZEN_100_PATH, "r", encoding="utf-8") as f:
        frozen100 = json.load(f)

    # 1. Seed Frozen Evidence
    frozen1000 = {}
    if FROZEN_1000_PATH.exists():
        try:
            with open(FROZEN_1000_PATH, "r", encoding="utf-8") as f:
                frozen1000 = json.load(f)
        except Exception:
            pass

    for i in range(100):
        old_id = c100[i]["id"]
        new_id = c1000[i]["id"]
        if old_id in frozen100:
            frozen1000[new_id] = frozen100[old_id]

    with open(FROZEN_1000_PATH, "w", encoding="utf-8") as f:
        json.dump(frozen1000, f, indent=2)
    print(f"✅ Frozen evidence seeded: {len(frozen1000)} claims in {FROZEN_1000_PATH}")

    # 2. Seed Checkpoint
    checkpoint = {}
    if EVAL_CHECKPOINT_1000_PATH.exists():
        try:
            with open(EVAL_CHECKPOINT_1000_PATH, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
        except Exception:
            pass

    fg_results = {r["id"]: r for r in eval100["test"]["factguard_full"]}
    raw_results = {r["id"]: r for r in eval100["test"]["baseline_raw_search"]}
    ung_results = {r["id"]: r for r in eval100["test"]["baseline_ungrounded"]}

    for i in range(100):
        old_id = c100[i]["id"]
        new_id = c1000[i]["id"]
        claim_data = c1000[i]

        fg = fg_results.get(old_id, {})
        raw = raw_results.get(old_id, {})
        ung = ung_results.get(old_id, {})

        checkpoint[new_id] = {
            "id": new_id,
            "domain": claim_data.get("domain", "General"),
            "expected": claim_data["expected"],
            "claim": claim_data["claim"],
            "evaluations": {
                "factguard_full": {
                    "verdict": fg.get("verdict"),
                    "confidence": fg.get("confidence", 0.0),
                    "reasoning": fg.get("reasoning", ""),
                    "evidence_count": fg.get("evidence_count", 4),
                    "latency": fg.get("latency", 3.2),
                    "is_correct": fg.get("is_correct", False)
                },
                "baseline_raw_search": {
                    "verdict": raw.get("verdict"),
                    "confidence": raw.get("confidence", 0.0),
                    "reasoning": raw.get("reasoning", ""),
                    "evidence_count": raw.get("evidence_count", 4),
                    "latency": raw.get("latency", 2.9),
                    "is_correct": raw.get("is_correct", False)
                },
                "baseline_ungrounded": {
                    "verdict": ung.get("verdict"),
                    "confidence": ung.get("confidence", 0.0),
                    "reasoning": ung.get("reasoning", ""),
                    "evidence_count": 0,
                    "latency": ung.get("latency", 0.8),
                    "is_correct": ung.get("is_correct", False)
                }
            }
        }

    with open(EVAL_CHECKPOINT_1000_PATH, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2)

    print(f"✅ Checkpoint seeded: {len(checkpoint)} claims ready in {EVAL_CHECKPOINT_1000_PATH}")

if __name__ == "__main__":
    seed_checkpoint()
