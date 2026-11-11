# tests/test_system_edge_cases.py
"""
FactGuard AI - System Architecture & Engineering Edge Case Test Suite
Tests:
1. ST-01: Stop-Word Collapse ("To be or not to be, that is the question")
2. ST-02: Special Characters & URL Delimiters ("C++", "&", "%")
3. ST-03: Viral Social Formatting (Emojis & Clickbait Punctuation)
4. ST-04: HTML & Script Injection Sanitization (<script> & <a> tags)
5. ST-05: Split-Truth Paragraph Evaluation (True fact + False myth)
6. ST-06: Concurrent Cache Persistence (Multi-threaded race condition safety)
"""

import sys
import os
import re
import json
import time
import threading
import unittest
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "backend"))

from core.claim_extractor import claim_extractor
from core.web_search import web_search
from core.cache import QueryCache
from factguard import FactGuard


class TestSystemEdgeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fg = FactGuard(api_url="http://127.0.0.1:8000")

    def test_st01_stop_word_collapse(self):
        """ST-01: Aggressive stop-word stripping must not collapse high-density quotes to < 2 words."""
        quote = "To be or not to be, that is the question."
        kw = web_search._extract_keywords(quote)
        print(f"\n[ST-01] Original: '{quote}' -> Keywords extracted: '{kw}'")
        words = kw.split()
        self.assertGreaterEqual(len(words), 3, "Keywords collapsed to fewer than 3 words!")

    def test_st02_special_characters_url_encoding(self):
        """ST-02: Special characters like 'C++', '&', and '%' must be safely preserved during query formulation."""
        query_cpp = "C++ is faster than Python for CPU-bound computations."
        query_amp = "Water is H2O & carbon dioxide is CO2."
        
        extracted_cpp = claim_extractor.extract(query_cpp)
        self.assertIn("C++", extracted_cpp, "C++ was stripped or mangled by claim extractor!")
        
        extracted_amp = claim_extractor.extract(query_amp)
        self.assertTrue("H2O" in extracted_amp and "CO2" in extracted_amp)
        print(f"\n[ST-02] Special characters preserved: '{extracted_cpp}' | '{extracted_amp}'")

    def test_st03_viral_social_formatting_emojis(self):
        """ST-03: Emojis and clickbait headers (BREAKING NEWS, !!) must be stripped without corrupting factual claim."""
        viral_input = "🚨🚨 BREAKING NEWS!! 😱 Bananas are naturally radioactive due to Potassium-40!! 🍌⚡️☢️ DO NOT PANIC!! 🤯💯"
        extracted = claim_extractor.extract(viral_input)
        print(f"\n[ST-03] Viral input cleaned: '{extracted}'")
        
        # Verify emojis are removed
        has_emojis = bool(re.search(r'[\U00010000-\U0010ffff]', extracted))
        self.assertFalse(has_emojis, f"Extracted claim still contains emojis: '{extracted}'")
        self.assertIn("Bananas", extracted)
        self.assertIn("Potassium-40", extracted)

    def test_st04_html_and_script_injection(self):
        """ST-04: Raw HTML and script tags must be completely stripped before parsing and search."""
        xss_input = "<script>alert('xss')</script> The Moon orbits around the Earth. <a href='http://malicious.site'>click</a>"
        extracted = claim_extractor.extract(xss_input)
        print(f"\n[ST-04] XSS input cleaned: '{extracted}'")
        
        self.assertNotIn("<script>", extracted)
        self.assertNotIn("alert", extracted)
        self.assertNotIn("<a", extracted)
        self.assertIn("Moon orbits", extracted)

    def test_st05_split_truth_paragraph(self):
        """ST-05: Multi-sentence paragraph containing both a True fact and a False myth."""
        split_paragraph = (
            "The Eiffel Tower is located in Paris, France. "
            "In addition, the Great Wall of China is visibly distinguishable from the surface of the Moon with the naked human eye."
        )
        extracted = claim_extractor.extract(split_paragraph)
        print(f"\n[ST-05] Split-truth paragraph extracted claim: '{extracted}'")
        self.assertTrue(len(extracted) > 0)

    def test_st06_concurrent_cache_persistence(self):
        """ST-06: Concurrent writes from multiple threads must never corrupt cache JSON file on disk."""
        test_cache_path = root_dir / "backend" / "data" / "test_concurrent_cache.json"
        if test_cache_path.exists():
            test_cache_path.unlink()

        cache = QueryCache(cache_path=test_cache_path)
        cache.cache = {}

        errors = []

        def worker(thread_id: int):
            try:
                for i in range(15):
                    claim = f"Thread-{thread_id} fact proposition number {i}"
                    result = {
                        "verdict": "True",
                        "confidence": 0.95,
                        "reasoning": f"Reasoning from thread {thread_id} run {i}"
                    }
                    cache.set(claim, result, user_id=f"user_{thread_id}")
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors occurred: {errors}")
        
        # Verify file is valid JSON
        self.assertTrue(test_cache_path.exists(), "Cache file was not created!")
        with open(test_cache_path, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
        self.assertIsInstance(loaded_data, dict)
        self.assertGreater(len(loaded_data), 0)
        print(f"\n[ST-06] Concurrent cache writes succeeded cleanly ({len(loaded_data)} entries preserved without corruption).")

        # Cleanup
        if test_cache_path.exists():
            test_cache_path.unlink()


if __name__ == "__main__":
    unittest.main()
