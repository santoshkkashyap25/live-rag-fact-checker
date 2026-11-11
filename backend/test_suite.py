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
from core.domain_trust import get_domain_trust, extract_domain
from core.visitor_tracker import VisitorTracker, visitor_tracker


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


class TestDomainTrustMatrix(unittest.TestCase):
    """Moat A: Domain Credibility & Authority Unit Tests"""

    def test_extract_domain(self):
        self.assertEqual(extract_domain("https://www.nature.com/articles/d41586"), "nature.com")
        self.assertEqual(extract_domain("http://en.wikipedia.org/wiki/Python"), "en.wikipedia.org")
        self.assertEqual(extract_domain("reddit.com/r/technology"), "reddit.com")

    def test_authoritative_tier(self):
        res = get_domain_trust("https://www.nature.com/articles/s41586")
        self.assertGreaterEqual(res["multiplier"], 1.5)
        self.assertFalse(res["is_satire"])
        self.assertIn("Tier 1", res["tier"])

        wiki_res = get_domain_trust("https://en.wikipedia.org/wiki/Science")
        self.assertGreaterEqual(wiki_res["multiplier"], 1.4)

        gov_res = get_domain_trust("https://cdc.gov/flu")
        self.assertGreaterEqual(gov_res["multiplier"], 1.5)

    def test_ugc_tier(self):
        res = get_domain_trust("https://medium.com/@user/my-claim")
        self.assertLessEqual(res["multiplier"], 0.4)
        self.assertIn("Tier 4", res["tier"])

    def test_satire_detection(self):
        res = get_domain_trust("https://theonion.com/scientists-discover-bananas-shoot-lasers")
        self.assertTrue(res["is_satire"])
        self.assertLessEqual(res["multiplier"], 0.1)
        self.assertIn("Satire", res["tier"])

    def test_domain_weighted_reranking(self):
        query = "bananas potassium radiation"
        items = [
            {"title": "Joke Post", "snippet": "Bananas cause laser radiation", "url": "https://theonion.com/joke", "source": "Web"},
            {"title": "Peer Study", "snippet": "Bananas contain naturally occurring potassium-40 radioactive isotope", "url": "https://nature.com/article", "source": "Web"},
            {"title": "Blog Post", "snippet": "Bananas are rich in potassium and healthy nutrients", "url": "https://medium.com/post", "source": "Web"}
        ]
        reranked = re_ranker.rerank_items(query, items, top_k=3)
        self.assertEqual(len(reranked), 3)
        top_item, top_score = reranked[0]
        # Nature study must be top-ranked due to 1.6x multiplier
        self.assertIn("nature.com", top_item["url"])
        self.assertGreater(top_score, 0)
        # The Onion must be lowest-ranked due to 0.05x multiplier
        last_item, last_score = reranked[-1]
        self.assertTrue(last_item["domain_trust"]["is_satire"])


class TestVisitorTracker(unittest.TestCase):
    """Test Privacy-Preserving Visitor & Usage Telemetry"""

    def setUp(self):
        import tempfile
        from pathlib import Path
        self.temp_file = Path(tempfile.gettempdir()) / "test_visitor_metrics.json"
        if self.temp_file.exists():
            self.temp_file.unlink()
        self.tracker = VisitorTracker(metrics_path=self.temp_file)

    def tearDown(self):
        if self.temp_file.exists():
            self.temp_file.unlink()

    def test_salted_hash_privacy(self):
        h1 = self.tracker._hash_ip("192.168.1.100")
        h2 = self.tracker._hash_ip("192.168.1.100")
        h3 = self.tracker._hash_ip("10.0.0.1")
        self.assertEqual(len(h1), 16)
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)
        self.assertNotIn("192", h1)

    def test_referrer_classification(self):
        self.assertEqual(self.tracker._classify_referrer("https://news.ycombinator.com/item?id=123"), "Hacker News")
        self.assertEqual(self.tracker._classify_referrer("https://www.linkedin.com/feed/"), "LinkedIn")
        self.assertEqual(self.tracker._classify_referrer("https://reddit.com/r/Python/"), "Reddit")
        self.assertEqual(self.tracker._classify_referrer("https://t.co/xyz123"), "Twitter / X")
        self.assertEqual(self.tracker._classify_referrer("https://x.com/post/456"), "Twitter / X")
        self.assertEqual(self.tracker._classify_referrer("https://github.com/santoshkkashyap25"), "GitHub")
        self.assertEqual(self.tracker._classify_referrer(None), "Direct / Search")

    def test_log_pageview_and_conversion(self):
        # 2 visitors from HN, 1 from LinkedIn
        self.tracker.log_pageview("1.1.1.1", path="/", referrer="https://news.ycombinator.com/")
        self.tracker.log_pageview("1.1.1.1", path="/analytics", referrer=None)  # repeat visit from same IP
        self.tracker.log_pageview("2.2.2.2", path="/", referrer="https://news.ycombinator.com/")
        self.tracker.log_pageview("3.3.3.3", path="/", referrer="https://linkedin.com/")

        # 1 executes verification
        self.tracker.log_verification("1.1.1.1", claim="Bananas are radioactive")

        summary = self.tracker.get_summary()
        self.assertEqual(summary["total_pageviews"], 4)
        self.assertEqual(summary["unique_visitors"], 3)
        self.assertEqual(summary["total_verifications"], 1)
        self.assertEqual(summary["conversion_rate_pct"], 25.0)
        self.assertEqual(summary["traffic_sources"]["Hacker News"], 2)
        self.assertEqual(summary["traffic_sources"]["LinkedIn"], 1)

    def test_disk_persistence(self):
        self.tracker.log_pageview("4.4.4.4", path="/", referrer="https://github.com")
        self.tracker.save_to_disk()

        tracker2 = VisitorTracker(metrics_path=self.temp_file)
        self.assertEqual(tracker2.total_pageviews, 1)
        self.assertEqual(tracker2.referrers["GitHub"], 1)


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
        self.assertIn("visitors", data)
        self.assertIn("cache", data)
        self.assertIn("database", data)
        self.assertIn("total_pageviews", data["visitors"])
        self.assertIn("traffic_sources", data["visitors"])

    def test_telemetry_visit_endpoint(self):
        res = self.client.post("/api/telemetry/visit", json={"path": "/analytics", "referrer": "https://news.ycombinator.com"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

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

