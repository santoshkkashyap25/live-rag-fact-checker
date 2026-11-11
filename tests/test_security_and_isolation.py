# tests/test_security_and_isolation.py
"""
FactGuard AI - Security, Sanitization & Cache Isolation Test Suite
Verifies:
1. Secret Sanitization: All cloud keys (Groq, OpenAI, Claude, Gemini) and bearer tokens are masked.
2. Custom Key Redaction: Arbitrary user keys in exceptions/strings are redacted.
3. Clean Key / Control Characters: Whitespace and CRLF characters that crash HTTP headers are scrubbed.
4. Ollama Endpoint Safeguard: Cloud API keys pasted into host URLs are caught and flagged.
5. Cache Provider/Model Isolation: Switching providers guarantees no cross-model cache poisoning.
6. Share Store Whitelisting: Private tokens/IDs cannot be stored in shared public cards.
"""

import sys
import unittest
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "backend"))

from core.security import sanitize_secrets, clean_api_key, is_probable_api_key
from core.cache import QueryCache
from core.share_store import ShareStore


class TestSecurityAndIsolation(unittest.TestCase):

    def test_sanitize_standard_api_keys(self):
        """Standard provider key prefixes must be redacted."""
        text = (
            "Error: Groq authentication failed with key gsk_abc12345678901234567890. "
            "Also checked sk-proj-12345678901234567890 and sk-ant-api03-abcdefghijklmn1234567890 "
            "and Google key AIzaSyABCDEF1234567890abcdefghijklmn."
        )
        sanitized = sanitize_secrets(text)
        
        self.assertNotIn("gsk_abc12345678901234567890", sanitized)
        self.assertIn("gsk_***", sanitized)
        self.assertNotIn("sk-proj-12345678901234567890", sanitized)
        self.assertIn("sk-***", sanitized)
        self.assertNotIn("sk-ant-api03-abcdefghijklmn1234567890", sanitized)
        self.assertIn("sk-ant-***", sanitized)
        self.assertNotIn("AIzaSyABCDEF1234567890abcdefghijklmn", sanitized)
        self.assertIn("AIzaSy***", sanitized)

    def test_sanitize_bearer_and_url_tokens(self):
        """Bearer tokens and URL query parameter credentials must be masked."""
        url_text = "GET https://generativelanguage.googleapis.com/v1beta/models?key=AIzaSyXYZ9876543210123456789"
        bearer_text = "Header 'Authorization': 'Bearer secret_user_token_1234567890'"
        
        clean_url = sanitize_secrets(url_text)
        clean_bearer = sanitize_secrets(bearer_text)
        
        self.assertNotIn("AIzaSyXYZ9876543210123456789", clean_url)
        self.assertIn("key=***", clean_url)
        self.assertNotIn("secret_user_token_1234567890", clean_bearer)
        self.assertIn("Bearer ***", clean_bearer)

    def test_sanitize_custom_key_redaction(self):
        """Arbitrary user custom keys in raw exception strings must be redacted."""
        custom_key = "custom_secret_enterprise_token_xyz999"
        error_msg = f"Failed to authenticate using key: {custom_key} at endpoint."
        
        sanitized = sanitize_secrets(error_msg, custom_keys=[custom_key])
        self.assertNotIn(custom_key, sanitized)
        self.assertIn(f"{custom_key[:4]}***", sanitized)

    def test_clean_api_key_crlf_stripping(self):
        """Control characters (\\r, \\n, \\t) and trailing whitespace must be removed."""
        dirty_key = "  \n\r  gsk_mycleansecretkey12345\t\n  "
        cleaned = clean_api_key(dirty_key)
        self.assertEqual(cleaned, "gsk_mycleansecretkey12345")

    def test_is_probable_api_key(self):
        """Check detection of accidental key paste into host fields."""
        self.assertTrue(is_probable_api_key("gsk_abc1234567890"))
        self.assertTrue(is_probable_api_key("sk-ant-api03-xyz"))
        self.assertTrue(is_probable_api_key("sk-proj-xyz"))
        self.assertTrue(is_probable_api_key("AIzaSyABCDEF"))
        
        self.assertFalse(is_probable_api_key("http://localhost:11434"))
        self.assertFalse(is_probable_api_key("http://192.168.1.100:11434"))
        self.assertFalse(is_probable_api_key("https://ollama.mycompany.internal"))
        self.assertFalse(is_probable_api_key(""))

    def test_cache_provider_model_isolation(self):
        """Cache must isolate verdicts by provider and model to avoid cross-engine pollution."""
        test_cache_path = root_dir / "backend" / "data" / "test_iso_cache.json"
        if test_cache_path.exists():
            test_cache_path.unlink()

        cache = QueryCache(cache_path=test_cache_path)
        cache.cache = {}

        claim = "The Moon orbits around the Earth."
        groq_result = {"verdict": "True", "engine": {"provider": "groq", "model": "compound-mini"}}
        claude_result = {"verdict": "True", "engine": {"provider": "claude", "model": "claude-sonnet-5.5"}}

        # Cache Groq result
        cache.set(claim, groq_result, user_id="usr_1", provider="groq", model="compound-mini")
        
        # Querying with claude must be a cache miss
        cached_for_claude = cache.get(claim, user_id="usr_1", provider="claude", model="claude-sonnet-5.5")
        self.assertIsNone(cached_for_claude, "Cross-provider cache collision: Groq returned for Claude!")

        # Querying with groq must be a cache hit
        cached_for_groq = cache.get(claim, user_id="usr_1", provider="groq", model="compound-mini")
        self.assertIsNotNone(cached_for_groq)
        self.assertEqual(cached_for_groq["engine"]["provider"], "groq")

        # Clean up
        if test_cache_path.exists():
            test_cache_path.unlink()

    def test_share_store_payload_whitelisting(self):
        """Sensitive fields in share request payloads must be strictly scrubbed."""
        test_share_path = root_dir / "backend" / "data" / "test_iso_share.json"
        if test_share_path.exists():
            test_share_path.unlink()

        store = ShareStore(store_path=test_share_path)
        store.store = {}

        tainted_payload = {
            "input_text": "Water is H2O",
            "extracted_claim": "Water is H2O",
            "verdict": "True",
            "confidence": 0.99,
            "reasoning": "Standard chemical formula.",
            "api_key": "sk-proj-leaked_secret_key_12345",
            "user_id": "usr_private_999",
            "client_ip": "192.168.1.1",
            "engine": {
                "provider": "groq",
                "model": "gpt-oss-120b",
                "api_key": "gsk_leaked_engine_key_12345"
            }
        }

        short_id = store.save_verdict(tainted_payload)
        saved = store.get_verdict(short_id)

        self.assertIsNotNone(saved)
        self.assertNotIn("api_key", saved, "Top-level api_key leaked into shared verdict!")
        self.assertNotIn("user_id", saved, "Top-level user_id leaked into shared verdict!")
        self.assertNotIn("client_ip", saved, "client_ip leaked into shared verdict!")
        self.assertNotIn("api_key", saved["engine"], "engine.api_key leaked into shared verdict!")
        self.assertEqual(saved["engine"]["provider"], "groq")

        # Clean up
        if test_share_path.exists():
            test_share_path.unlink()


if __name__ == "__main__":
    unittest.main()

