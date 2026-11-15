import os
import re
from dotenv import load_dotenv
import groq

load_dotenv("backend/.env")

key_pool = []
for env_var in ["GROQ_API_KEYS", "GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3"]:
    val = os.environ.get(env_var, "")
    if val:
        parts = [k.strip() for k in re.split(r"[,;\s]+", val) if k.strip().startswith("gsk_")]
        key_pool.extend(parts)
key_pool = list(dict.fromkeys(key_pool))

print(f"Testing {len(key_pool)} Groq API keys in pool:\n")

models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]

for idx, key in enumerate(key_pool, 1):
    tag = f"...{key[-6:]}"
    print(f"--- Key #{idx} [{tag}] ---")
    client = groq.Groq(api_key=key)
    for m in models:
        try:
            resp = client.chat.completions.with_raw_response.create(
                model=m,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5
            )
            rem_req = resp.headers.get("x-ratelimit-remaining-requests")
            rem_tok = resp.headers.get("x-ratelimit-remaining-tokens")
            print(f"  ✅ {m:20s}: OK! Remaining req: {rem_req}, Remaining TPM: {rem_tok}")
        except Exception as e:
            print(f"  ❌ {m:20s}: {str(e)[:100]}")
    print()
