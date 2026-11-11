# core/security.py
"""
FactGuard AI - Security, Privacy & Secret Sanitization Module
Guarantees:
- Zero API key leakage into logs, exceptions, responses, shared cards, or telemetry.
- Cleans and strips trailing/leading whitespace and CRLF control characters from BYOK keys.
- Detects API keys mistakenly entered into endpoint/host input fields.
"""

import re
from typing import Optional, List, Any

# Regular expressions for common LLM API keys and sensitive tokens
API_KEY_PATTERNS = [
    # Query parameter credentials (e.g. key=... or api_key=...)
    (re.compile(r'([?&](?:api_)?key=)[^& \t\r\n]{6,}', re.IGNORECASE), r'\1***'),
    # Bearer authorization headers
    (re.compile(r'(Bearer\s+)[a-zA-Z0-9_\-\.]{10,}', re.IGNORECASE), r'\1***'),
    # Authorization header fragments in error messages
    (re.compile(r"('authorization':\s*'Bearer\s+)[^']+", re.IGNORECASE), r"\1***'"),
    (re.compile(r'("authorization":\s*"Bearer\s+)[^"]+', re.IGNORECASE), r'\1***"'),
    # Groq API keys (gsk_...)
    (re.compile(r'\b(gsk_)[a-zA-Z0-9_\-]{15,}\b', re.IGNORECASE), r'\1***'),
    # Anthropic API keys (sk-ant-...)
    (re.compile(r'\b(sk-ant-[a-zA-Z0-9_\-]{20,})\b', re.IGNORECASE), r'sk-ant-***'),
    # OpenAI API keys (sk-proj-... or sk-...)
    (re.compile(r'\b(sk-(?:proj-)?[a-zA-Z0-9_\-]{15,})\b', re.IGNORECASE), r'sk-***'),
    # Google Gemini / Cloud API keys (AIzaSy...)
    (re.compile(r'\b(AIzaSy)[a-zA-Z0-9_\-]{20,}\b', re.IGNORECASE), r'\1***'),
]

def sanitize_secrets(text: Any, custom_keys: Optional[List[Optional[str]]] = None) -> str:
    """
    Scrub all known API key patterns and custom keys from text.
    Safe for use on error messages, logs, reasoning strings, and shared verdicts.
    """
    if text is None:
        return ""
    
    clean_text = str(text)
    
    # 1. Redact custom keys provided by the caller
    if custom_keys:
        for k in custom_keys:
            if k and isinstance(k, str):
                s = k.strip()
                if len(s) >= 6:
                    clean_text = clean_text.replace(s, f"{s[:4]}***")

    # 2. Apply general regex redactions
    for pattern, replacement in API_KEY_PATTERNS:
        clean_text = pattern.sub(replacement, clean_text)

    return clean_text

def clean_api_key(key: Optional[str]) -> str:
    """
    Trim whitespace and strip CRLF/tab characters that break HTTP headers.
    """
    if not key:
        return ""
    return re.sub(r'[\r\n\t]', '', str(key)).strip()

def is_probable_api_key(val: Optional[str]) -> bool:
    """
    Check if a value looks like a secret API key rather than a valid URL or host.
    """
    if not val:
        return False
    v = val.strip()
    return bool(
        v.startswith("gsk_") or
        v.startswith("sk-ant-") or
        v.startswith("sk-proj-") or
        v.startswith("sk-") or
        v.startswith("AIzaSy")
    )
