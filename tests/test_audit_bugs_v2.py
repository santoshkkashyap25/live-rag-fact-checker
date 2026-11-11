# tests/test_audit_bugs_v2.py
"""
FactGuard AI - Deep Bug Audit Test Suite (Phase 2)
Tests:
1. Resilient JSON & Heuristic LLM Output Parsing
2. Copula (AUX) Verb Dependency Parsing ("is", "are", "was", "were")
3. Unicode Mathematical / Fullwidth Homoglyph De-obfuscation
4. Web Search Compound Conjunction Splitting Edge Cases (No IndexError)
5. Re-ranker Positional 1:1 Item Alignment (No Text Collision)
6. Non-Destructive Multi-Tenant Cache Clear Safeguard
"""

import sys
import unittest
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "backend"))

from core.llm_service import llm_service
from core.claim_extractor import claim_extractor
from core.web_search import web_search
from core.re_ranker import re_ranker
from core.cache import QueryCache


class TestAuditBugsV2(unittest.TestCase):

    def test_extract_json_conversational_text_and_trailing_commas(self):
        """Balanced brace parser must handle conversational preamble and trailing commas."""
        text = (
            "Here is the evaluation result you requested:\n\n"
            "{\n"
            '  "verdict": "True",\n'
            '  "confidence": 0.95,\n'
            '  "reasoning": "Confirmed by multiple authoritative sources.",\n'
            "}\n\n"
            "Hope this helps! Let me know if you need more details {like citations}."
        )
        parsed = llm_service._extract_json(text)
        self.assertEqual(parsed.get("verdict"), "True")
        self.assertEqual(parsed.get("confidence"), 0.95)
        self.assertIn("authoritative", parsed.get("reasoning", ""))

    def test_extract_json_heuristic_plaintext_fallback(self):
        """When an LLM produces plain key-value text instead of JSON, extract values gracefully."""
        plaintext = (
            "Verdict: False\n"
            "Confidence: 90%\n"
            "Reasoning: The Great Wall is not visible from the Moon with the naked human eye."
        )
        parsed = llm_service._extract_json(plaintext)
        self.assertEqual(parsed.get("verdict"), "False")
        self.assertAlmostEqual(parsed.get("confidence"), 0.90)
        self.assertIn("naked human eye", parsed.get("reasoning", ""))

    def test_copula_aux_dependency_parsing(self):
        """Copular auxiliary verbs ('is', 'are', 'was', 'were') must be recognized by dependency parsing."""
        claim_input = "It is widely believed that Paris is the capital of France."
        extracted = claim_extractor.extract(claim_input)
        self.assertIn("Paris", extracted)
        self.assertIn("capital of France", extracted)

    def test_mathematical_fullwidth_unicode_homoglyphs(self):
        """Fullwidth letters and mathematical bold Unicode characters must be decomposed."""
        # '𝐅ａｃｔ' contains mathematical bold 'F' and fullwidth 'a', 'c', 't'
        obfuscated = "𝐅ａｃｔ: Water boils at 100 degrees Celsius."
        extracted = claim_extractor.extract(obfuscated)
        self.assertIn("Water boils", extracted)
        # Ensure no fullwidth or mathematical bold letters remain
        self.assertNotIn("\uff41", extracted)  # fullwidth 'a'

    def test_web_search_compound_edge_cases(self):
        """Malformed compound conjunction queries must not crash with IndexError."""
        # Starts with conjunction or delimiter
        edge_queries = [
            ", and bananas are naturally radioactive.",
            "; water boils at high heat",
            "and nitrogen is 78% of air",
            ", but the earth revolves around the sun"
        ]
        for q in edge_queries:
            try:
                # Test query formulation without throwing IndexError
                results = web_search.search(q, max_results=3)
                self.assertIsInstance(results, list)
            except IndexError as ie:
                self.fail(f"web_search.search threw IndexError on '{q}': {ie}")

    def test_reranker_positional_alignment_with_duplicate_texts(self):
        """Multiple items with identical snippets must not collide or lose items."""
        items = [
            {"title": "Fact 1", "snippet": "Identical snippet text for testing.", "url": "https://source1.org"},
            {"title": "Fact 2", "snippet": "Identical snippet text for testing.", "url": "https://source2.org"},
            {"title": "Fact 3", "snippet": "Unique snippet about physics.", "url": "https://source3.org"},
        ]
        ranked = re_ranker.rerank_items("Identical snippet", items, top_k=3)
        self.assertEqual(len(ranked), 3)
        # Ensure both source 1 and source 2 are preserved
        urls = [item["url"] for item, _ in ranked]
        self.assertIn("https://source1.org", urls)
        self.assertIn("https://source2.org", urls)

    def test_cache_clear_multi_tenant_safeguard(self):
        """Clearing cache without explicit all_users flag must not wipe all users."""
        test_cache_path = root_dir / "backend" / "data" / "test_safe_clear_cache.json"
        if test_cache_path.exists():
            test_cache_path.unlink()

        cache = QueryCache(cache_path=test_cache_path)
        cache.set("Claim 1", {"verdict": "True"}, user_id="user_alice")
        cache.set("Claim 2", {"verdict": "False"}, user_id="user_bob")

        # Clear only user_alice
        cache.clear(user_id="user_alice")

        # user_bob's cache must remain intact
        bob_cached = cache.get("Claim 2", user_id="user_bob")
        self.assertIsNotNone(bob_cached, "user_bob's cache was wiped during user_alice's clear!")

        # Clean up
        if test_cache_path.exists():
            test_cache_path.unlink()

    def test_negation_and_auxiliary_preservation(self):
        """Dependency parsing must preserve negations ('not', 'never') and auxiliary verbs without inversion."""
        nlp = claim_extractor._get_nlp()
        
        # Test 1: Copula with negation
        doc1 = nlp("Bananas are definitely not radioactive.")
        parsed1 = claim_extractor._extract_via_dependency_parsing(doc1)
        self.assertIsNotNone(parsed1)
        self.assertIn("not", parsed1.lower(), "Negation 'not' was stripped from claim!")
        self.assertIn("radioactive", parsed1.lower())

        # Test 2: Temporal negation before verb
        doc2 = nlp("Lightning never strikes the same place twice.")
        parsed2 = claim_extractor._extract_via_dependency_parsing(doc2)
        self.assertIsNotNone(parsed2)
        self.assertIn("never", parsed2.lower(), "Negation 'never' was stripped from claim!")
        self.assertTrue(parsed2.lower().index("never") < parsed2.lower().index("strikes"), "Word order scrambled!")

        # Test 3: Auxiliary + negation
        doc3 = nlp("The Earth does not revolve around Mars.")
        parsed3 = claim_extractor._extract_via_dependency_parsing(doc3)
        self.assertIsNotNone(parsed3)
        self.assertIn("not", parsed3.lower())
        self.assertIn("does", parsed3.lower())

    def test_sdk_langchain_core_tool_export(self):
        """FactGuard SDK as_langchain_tool must succeed with modern langchain-core."""
        from factguard import FactGuard
        fg = FactGuard()
        try:
            tool = fg.as_langchain_tool()
            self.assertEqual(tool.name, "factguard_verifier")
            self.assertIn("DuckDuckGo", tool.description)
        except ImportError as e:
            # Only allowed if neither langchain nor langchain-core is installed
            self.assertIn("LangChain is not installed", str(e))


if __name__ == "__main__":
    unittest.main()
