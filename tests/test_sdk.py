# tests/test_sdk.py
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from factguard import FactGuard, FactCheckResult

class TestFactGuardSDK(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Point SDK to local test server
        cls.fg = FactGuard(api_url="http://127.0.0.1:8000")

    def test_sdk_verify(self):
        result = self.fg.verify("Bananas contain potassium.")
        self.assertIsInstance(result, FactCheckResult)
        self.assertIn(result.verdict, ["True", "False", "Unverifiable"])
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertIsInstance(result.reasoning, str)
        self.assertIsInstance(result.evidence, list)

    def test_sdk_stream(self):
        events = list(self.fg.stream("Bananas contain potassium."))
        self.assertGreater(len(events), 0)
        types = [e.get("type") for e in events]
        self.assertIn("status", types)
        self.assertIn("complete", types)

    def test_sdk_share(self):
        result = self.fg.verify("Bananas contain potassium.")
        share_url = self.fg.share(result)
        self.assertTrue(share_url.startswith("http"))
        self.assertIn("/v/", share_url)

if __name__ == "__main__":
    unittest.main()
