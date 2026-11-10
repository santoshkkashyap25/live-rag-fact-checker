# tests/test_sdk.py
import sys
import time
import threading
import requests
import unittest
from pathlib import Path

# Add project root and backend to sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(backend_dir))

from factguard import FactGuard, FactCheckResult

class TestFactGuardSDK(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Ensure local test server is running on 8000
        is_running = False
        try:
            r = requests.get("http://127.0.0.1:8000/health", timeout=1)
            is_running = (r.status_code == 200)
        except Exception:
            is_running = False

        if not is_running:
            import uvicorn
            from main import app
            config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
            server = uvicorn.Server(config)
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()

            for _ in range(30):
                try:
                    if requests.get("http://127.0.0.1:8000/health", timeout=0.5).status_code == 200:
                        break
                except Exception:
                    time.sleep(0.1)

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

    def test_sdk_tool_exports(self):
        try:
            tool = self.fg.as_langchain_tool()
            self.assertEqual(tool.name, "factguard_verifier")
        except ImportError as e:
            self.assertIn("LangChain is not installed", str(e))

        try:
            tool = self.fg.as_llamaindex_tool()
            self.assertEqual(tool.metadata.name, "factguard_verifier")
        except ImportError as e:
            self.assertIn("LlamaIndex is not installed", str(e))

if __name__ == "__main__":
    unittest.main()
