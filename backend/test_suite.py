"""
FactGuard AI - Comprehensive Automated Test Suite
Tests backend components, core algorithms, API endpoints, and static UI delivery.
"""

import sys
import os
import unittest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from core.claim_extractor import claim_extractor
from core.cache import QueryCache
from core.re_ranker import re_ranker
from core.web_search import web_search


class TestClaimExtractor(unittest.TestCase):
    def test_atomic_claim(self):
        text = "Water boils at 100 degrees Celsius."
        claim = claim_extractor.extract(text)
        self.assertIsInstance(claim, str)
        self.assertTrue(len(claim) > 0)
        self.assertIn("Water", claim)

    def test_multi_sentence_extraction(self):
        text = "Hello everyone! The Earth revolves around the Sun. Have a great day!"
        claim = claim_extractor.extract(text)
        self.assertIn("Earth", claim)


class TestQueryCache(unittest.TestCase):
    def setUp(self):
        self.cache = QueryCache()
        self.cache.cache = {}

    def test_set_and_get(self):
        payload = {"verdict": "True", "confidence": "0.95"}
        self.cache.set("The Moon orbits the Earth.", payload, user_id="user_1")
        cached = self.cache.get("The Moon orbits the Earth.", user_id="user_1")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["verdict"], "True")

    def test_user_isolation(self):
        payload = {"verdict": "True", "confidence": "0.95"}
        self.cache.set("Isolation claim", payload, user_id="user_A")
        # Different user should not see user_A's cache
        cached_b = self.cache.get("Isolation claim", user_id="user_B")
        self.assertIsNone(cached_b)

    def test_clear_user_cache(self):
        self.cache.set("Claim 1", {"v": 1}, user_id="user_clear")
        self.cache.clear(user_id="user_clear")
        self.assertIsNone(self.cache.get("Claim 1", user_id="user_clear"))


class TestReRanker(unittest.TestCase):
    def test_bm25_ranking(self):
        query = "Python programming language Guido van Rossum"
        docs = [
            "Bananas are yellow fruit grown in tropical regions.",
            "Python was created by Guido van Rossum and first released in 1991.",
            "The capital of France is Paris."
        ]
        results = re_ranker.rerank(query, docs, top_k=2)
        self.assertTrue(len(results) <= 2)
        top_doc, top_score = results[0]
        self.assertIn("Guido van Rossum", top_doc)
        self.assertTrue(top_score > 0)


class TestAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("app"), "LLM-Powered Fact Checker")

    def test_api_health_check(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("status"), "healthy")

    def test_examples_endpoint(self):
        res = self.client.get("/api/examples")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("examples", data)
        self.assertTrue(len(data["examples"]) >= 3)

    def test_static_root_delivery(self):
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        if os.path.exists(static_dir):
            self.assertIn("text/html", res.headers.get("content-type", ""))
            self.assertIn("<!DOCTYPE html>", res.text)
        else:
            data = res.json()
            self.assertEqual(data.get("mode"), "api_only")

    def test_static_analytics_delivery(self):
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        if not os.path.exists(static_dir):
            self.skipTest("Static assets not built in clean checkout (api_only mode)")
        res = self.client.get("/analytics/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers.get("content-type", ""))
        self.assertNotIn("Web Intelligence Engine", res.text)

    def test_analytics_api(self):
        res = self.client.get("/api/analytics")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("summary", data)
        self.assertIn("cache", data)
        self.assertIn("database", data)

    def test_verify_pipeline(self):
        payload = {
            "text": "The Digital India initiative was launched in 2015.",
            "user_id": "test_suite_user"
        }
        res = self.client.post("/api/verify", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("verdict", data)
        self.assertIn(data["verdict"], ["True", "False", "Unverifiable"])
        self.assertIn("confidence", data)
        self.assertIn("performance", data)
        self.assertIn("evidence", data)
        self.assertIsInstance(data["evidence"], list)

    def test_verify_stream_endpoint(self):
        payload = {
            "text": "The Digital India initiative was launched in 2015.",
            "user_id": "test_suite_user_stream"
        }
        res = self.client.post("/api/verify/stream", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/event-stream", res.headers.get("content-type", ""))
        self.assertIn("data: ", res.text)

    def test_share_endpoints(self):
        payload = {
            "result": {
                "input_text": "Bananas contain potassium.",
                "extracted_claim": "Bananas contain potassium",
                "verdict": "True",
                "confidence": 0.95,
                "reasoning": "Scientific evidence confirms potassium in bananas.",
                "evidence": ["Bananas are rich in potassium."],
                "evidence_sources": ["Wikipedia"],
                "evidence_urls": ["https://en.wikipedia.org/wiki/Banana"]
            }
        }
        # POST /api/share
        res = self.client.post("/api/share", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("id", data)
        self.assertIn("url", data)
        share_id = data["id"]

        # GET /api/share/{share_id}
        get_res = self.client.get(f"/api/share/{share_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["verdict"], "True")

        # GET /v/{share_id} (Server-Rendered HTML)
        html_res = self.client.get(f"/v/{share_id}")
        self.assertEqual(html_res.status_code, 200)
        self.assertIn("text/html", html_res.headers.get("content-type", ""))
        self.assertIn("og:title", html_res.text)
        self.assertIn("FactGuard", html_res.text)

        # GET /api/og/{share_id}.svg (Dynamic SVG Card)
        svg_res = self.client.get(f"/api/og/{share_id}.svg")
        self.assertEqual(svg_res.status_code, 200)
        self.assertIn("image/svg+xml", svg_res.headers.get("content-type", ""))
        self.assertIn("<svg", svg_res.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)

