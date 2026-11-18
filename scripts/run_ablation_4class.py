import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath('backend'))

from core.llm_service import llm_service
from core.security import clean_api_key

def run_ablation():
    dump_path = 'scripts/unv_false_32_dump.json'
    if not os.path.exists(dump_path):
        print(f"File not found: {dump_path}")
        return

    with open(dump_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)

    print(f"🚀 Running 4-class prompt ablation on {len(cases)} previously overreached claims...")
    print(f"Using prompt version: {llm_service.PROMPT_VERSION} (hash: {llm_service.prompt_hash})\n")

    results = []
    migrated_to_unsupported = 0
    migrated_to_unverifiable = 0
    remained_false = 0
    other_verdict = 0

    for idx, c in enumerate(cases, 1):
        cid = c['id']
        claim = c['claim']
        domain = c['domain']
        evidence_snippets = c.get('evidence_snippets', [])

        print(f"[{idx}/{len(cases)}] Evaluating {cid} ({domain}): {claim[:65]}...")
        time.sleep(1.0) # gentle pacing

        try:
            res = llm_service.get_verdict(claim, evidence=evidence_snippets, provider="groq")
            new_v = res.verdict
            new_c = res.confidence
            new_r = res.reasoning
        except Exception as e:
            print(f"  Error: {e}")
            new_v, new_c, new_r = "Error", 0.0, str(e)

        if new_v == "Unsupported":
            migrated_to_unsupported += 1
            icon = "🟠"
        elif new_v == "Unverifiable":
            migrated_to_unverifiable += 1
            icon = "⚪"
        elif new_v == "False":
            remained_false += 1
            icon = "🔴"
        else:
            other_verdict += 1
            icon = "❓"

        print(f"  Old: 🔴 False  -->  New: {icon} {new_v} (Conf: {new_c:.2f})")
        print(f"  Reasoning: {new_r[:120]}...\n")

        results.append({
            "id": cid,
            "claim": claim,
            "domain": domain,
            "old_verdict": "False",
            "new_verdict": new_v,
            "new_confidence": new_c,
            "new_reasoning": new_r
        })

    print("=" * 60)
    print("📊 ABLATION SUMMARY ON THE 32 OVERREACH CASES")
    print("=" * 60)
    print(f"Total claims evaluated: {len(cases)}")
    print(f"Migrated to Unsupported:  {migrated_to_unsupported} ({migrated_to_unsupported/len(cases)*100:.1f}%)")
    print(f"Migrated to Unverifiable: {migrated_to_unverifiable} ({migrated_to_unverifiable/len(cases)*100:.1f}%)")
    print(f"Remained False:           {remained_false} ({remained_false/len(cases)*100:.1f}%)")
    print(f"Other (e.g. True/Error):  {other_verdict} ({other_verdict/len(cases)*100:.1f}%)")
    
    out_path = 'scripts/ablation_32_results.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({
            "prompt_version": llm_service.PROMPT_VERSION,
            "prompt_hash": llm_service.prompt_hash,
            "migrated_to_unsupported": migrated_to_unsupported,
            "migrated_to_unverifiable": migrated_to_unverifiable,
            "remained_false": remained_false,
            "other_verdict": other_verdict,
            "details": results
        }, f, indent=2)
    print(f"Detailed results saved to {out_path}")

if __name__ == "__main__":
    run_ablation()
