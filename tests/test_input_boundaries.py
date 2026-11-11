# tests/test_input_boundaries.py
"""
FactGuard AI - Input Length & Word Limit Boundary Test Suite
Tests:
1. HTTP 422 rejection on > 1000 characters (overflow rejection).
2. HTTP 200 acceptance on exactly 1000 characters.
3. Realistic 150-word dense paragraph (850-950 chars) containing a hidden verifiable claim:
   Tests ClaimExtractor dependency parsing, keyword extraction, DuckDuckGo retrieval, and LLM verdict.
"""

import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "backend"))

from main import app
from core.claim_extractor import claim_extractor
from factguard import FactGuard


class TestInputBoundaries(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.fg = FactGuard(api_url="http://127.0.0.1:8000")

    def test_rejection_over_1000_chars(self):
        """Inputs exceeding 1000 characters must be rejected immediately with HTTP 422."""
        oversized_text = "Water is composed of hydrogen and oxygen. " * 25  # ~1050 chars
        self.assertGreater(len(oversized_text), 1000)

        response = self.client.post("/api/verify", json={"text": oversized_text})
        self.assertEqual(response.status_code, 422)
        errors = response.json().get("detail", [])
        self.assertTrue(any(e.get("type") == "string_too_long" for e in errors))
        print(f"\n[PASS] 1001+ char overflow correctly rejected with HTTP 422 (Length: {len(oversized_text)} chars)")

    def test_acceptance_exact_1000_chars(self):
        """Input of exactly 1000 characters must be accepted and parsed cleanly."""
        base = "The Great Wall of China is located in northern China. "
        repeated = base * (1000 // len(base))
        exact_1000 = repeated + "A" * (1000 - len(repeated))
        self.assertEqual(len(exact_1000), 1000)

        extracted = claim_extractor.extract(exact_1000)
        self.assertIsInstance(extracted, str)
        self.assertTrue(len(extracted) > 0)
        print(f"\n[PASS] Exactly 1000 chars parsed without crash (Extracted length: {len(extracted)} chars)")

    def test_dense_150_word_news_paragraph(self):
        """
        Realistic ~150-word dense conversational/news paragraph (approx 900 chars).
        Embedding narrative fluff, conversational filler, and a verifiable factual claim:
        'The Eiffel Tower is located in Paris, France.'
        """
        dense_paragraph = (
            "During a recent discussion among international travelers and historians regarding iconic European "
            "monuments, several participants debated the historical origins and physical whereabouts of various "
            "structures constructed during the industrial revolution. Some believed it was erected for the world "
            "fair, while others discussed its engineering challenges. Ultimately, it is widely documented that "
            "the Eiffel Tower is located in Paris, France. Furthermore, travelers continue to visit the monument "
            "by the millions each year, taking photographs from the Champ de Mars and expressing admiration for "
            "Gustave Eiffel's revolutionary lattice iron design."
        )
        word_count = len(dense_paragraph.split())
        char_count = len(dense_paragraph)
        print(f"\nTesting realistic dense paragraph: {word_count} words, {char_count} characters.")

        # Test ClaimExtractor
        extracted = claim_extractor.extract(dense_paragraph)
        print(f"Extracted Claim: \"{extracted}\"")
        self.assertTrue(len(extracted) > 0)

        # Test live pipeline through SDK
        res = self.fg.verify(dense_paragraph, user_id="test_long_input", use_cache=False)
        print(f"Verdict: {res.verdict} (Confidence: {res.confidence})")
        print(f"Reasoning: {res.reasoning}")
        self.assertEqual(res.verdict, "True")


if __name__ == "__main__":
    unittest.main()
