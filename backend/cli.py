"""
FactGuard AI - Command Line Interface
Usage:
    python cli.py "India has 28 states and 8 union territories."
    python cli.py --help
"""

import sys
import argparse
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from pipeline import run_fact_checking_pipeline

def main():
    parser = argparse.ArgumentParser(
        description="FactGuard AI: CLI Fact-Checking Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py "India has 28 states and 8 union territories."
  python cli.py "The Digital India initiative was launched in 2015."
        """
    )
    parser.add_argument(
        "statement",
        type=str,
        nargs="?",
        help="The claim or statement to verify"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass the query cache and re-verify"
    )

    args = parser.parse_args()

    statement = args.statement
    if not statement:
        statement = input("\nEnter claim or statement to verify: ").strip()

    if not statement:
        print("[ERROR] Statement cannot be empty.")
        sys.exit(1)

    print("=" * 70)
    print(f"FactGuard AI - Fact Verification")
    print("=" * 70)
    print(f"Claim: {statement}\n")

    try:
        result = run_fact_checking_pipeline(statement, use_cache=not args.no_cache)
        
        verdict = result.get("verdict", "Unverifiable")
        confidence = result.get("confidence", "0.00")
        reasoning = result.get("reasoning", "")
        evidence = result.get("evidence", [])
        perf = result.get("performance", {})
        
        print("-" * 70)
        print(f"VERDICT:    {verdict}")
        print(f"CONFIDENCE: {float(confidence) * 100:.1f}%")
        print(f"CLAIM:      {result.get('extracted_claim')}")
        print(f"REASONING:  {reasoning}")
        print("-" * 70)
        
        if evidence:
            print(f"RETRIEVED EVIDENCE ({len(evidence)} items):")
            scores = result.get("evidence_scores", [])
            for i, ev in enumerate(evidence):
                score_str = f" [score: {scores[i]}]" if i < len(scores) else ""
                print(f"  [{i+1}]{score_str} {ev}")
        
        print("-" * 70)
        print(f"TIMING: Extraction: {perf.get('extraction_time', 'N/A')}, "
              f"Retrieval: {perf.get('retrieval_time', 'N/A')}, "
              f"LLM: {perf.get('llm_time', 'N/A')}, "
              f"Total: {perf.get('total_time', 'N/A')}")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
