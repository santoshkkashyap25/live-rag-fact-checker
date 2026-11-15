import os
from dotenv import load_dotenv
import groq

load_dotenv("backend/.env")
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))

models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "allam-2-7b"]
for m in models:
    try:
        resp = client.chat.completions.with_raw_response.create(
            model=m,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5
        )
        print(f"✅ {m}: OK! Remaining req: {resp.headers.get('x-ratelimit-remaining-requests')}, Remaining tokens: {resp.headers.get('x-ratelimit-remaining-tokens')}")
    except Exception as e:
        print(f"❌ {m}: {str(e)[:120]}")
