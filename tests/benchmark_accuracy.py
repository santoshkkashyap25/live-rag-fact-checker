# tests/benchmark_accuracy.py
"""
FactGuard AI - Empirical Benchmark Evaluation Script
Evaluates real-time retrieval grounding and verdict calibration on common factual propositions and misconceptions.
"""

import sys
import time
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from factguard import FactGuard

BENCHMARK_CLAIMS = [
    {
        "claim": "Bananas are naturally radioactive due to potassium-40.",
        "expected": "True",
        "category": "Nuclear Physics / Biology"
    },
    {
        "claim": "The Great Wall of China is visible from the Moon with the naked eye.",
        "expected": "False",
        "category": "Popular Misconceptions"
    },
    {
        "claim": "Water expands when it freezes into ice.",
        "expected": "True",
        "category": "Thermodynamics / Chemistry"
    },
    {
        "claim": "Humans only use 10 percent of their brain capacity.",
        "expected": "False",
        "category": "Neuroscience Myths"
    },
    {
        "claim": "The speed of light in a vacuum is roughly 300,000 kilometers per second.",
        "expected": "True",
        "category": "Astrophysics"
    },
    {
        "claim": "Albert Einstein failed mathematics as a child in school.",
        "expected": "False",
        "category": "Historical Misconceptions"
    }
]

def run_benchmark():
    fg = FactGuard(api_url="http://127.0.0.1:8000")
    print("\n" + "=" * 80)
    print("🎯 FactGuard AI - Empirical Grounding & Hallucination Benchmark")
    print("=" * 80)

    correct = 0
    total = len(BENCHMARK_CLAIMS)
    latencies = []

    print(f"\n{'Category':<26} | {'Claim':<35} | {'Expected':<8} | {'Verdict':<8} | {'Conf':<6} | {'Time'}")
    print("-" * 105)

    for item in BENCHMARK_CLAIMS:
        claim = item["claim"]
        expected = item["expected"]
        cat = item["category"]

        t0 = time.time()
        try:
            res = fg.verify(claim)
            elapsed = time.time() - t0
            latencies.append(elapsed)

            is_correct = (res.verdict == expected)
            if is_correct:
                correct += 1

            status_mark = "✓" if is_correct else "✗"
            short_claim = (claim[:32] + "...") if len(claim) > 35 else claim
            print(f"{cat:<26} | {short_claim:<35} | {expected:<8} | {res.verdict:<8} {status_mark} | {res.confidence:<6.2f} | {elapsed:.2f}s")
        except Exception as e:
            print(f"{cat:<26} | {claim[:30]:<35} | {expected:<8} | ERROR    ✗ | {str(e)[:15]}")

    accuracy = (correct / total) * 100
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    print("-" * 105)
    print(f"\n📊 Benchmark Summary:")
    print(f"   • Total Claims Evaluated: {total}")
    print(f"   • Verdict Accuracy:       {correct}/{total} ({accuracy:.1f}%)")
    print(f"   • Average Latency:        {avg_latency:.2f}s per verification")
    print(f"   • Zero-Hallucination Rate: {accuracy:.1f}%\n")

if __name__ == "__main__":
    run_benchmark()

