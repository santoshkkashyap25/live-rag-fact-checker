# core/visitor_tracker.py
"""
FactGuard AI - Native Privacy-Preserving Visitor & Usage Telemetry
Tracks:
- Total Pageviews (homepage, analytics, share links)
- Unique Daily & All-Time Visitors (Salted SHA256 hashed IP for GDPR compliance)
- Traffic Referrer Attribution (Hacker News, LinkedIn, Reddit, Twitter/X, GitHub, Direct)
- Verification Funnel Conversion Rate (% of visitors who run a fact-check)
- Atomic disk persistence with optional remote KV backup hook
"""

import os
import json
import time
import hashlib
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_VISITOR_METRICS_PATH = DATA_DIR / "visitor_metrics.json"


class VisitorTracker:
    def __init__(self, metrics_path: Optional[Path] = None):
        self.metrics_path = Path(metrics_path) if metrics_path else DEFAULT_VISITOR_METRICS_PATH
        self._lock = threading.RLock()
        
        # State
        self.total_pageviews: int = 0
        self.total_verifications: int = 0
        self.unique_visitors: set = set()  # set of 16-char hashes
        self.daily_unique: Dict[str, set] = {}  # YYYY-MM-DD -> set of hashes
        self.referrers: Dict[str, int] = {
            "Hacker News": 0,
            "LinkedIn": 0,
            "Reddit": 0,
            "Twitter / X": 0,
            "GitHub": 0,
            "Direct / Search": 0,
            "Other": 0
        }
        self.recent_activity: List[Dict[str, Any]] = []
        
        # Load existing state
        self.load_from_disk()

    def _hash_ip(self, client_ip: str) -> str:
        """Create privacy-compliant salted hash of client IP. Never stores raw IPs."""
        salt = os.getenv("VISITOR_SALT", "factguard_telemetry_salt_2026")
        return hashlib.sha256(f"{salt}:{client_ip}".encode()).hexdigest()[:16]

    def _classify_referrer(self, referrer_url: Optional[str]) -> str:
        """Classify referrer URL into primary launch channel sources."""
        if not referrer_url:
            return "Direct / Search"
        
        ref = referrer_url.lower()
        if "ycombinator" in ref or "hacker" in ref:
            return "Hacker News"
        elif "linkedin" in ref or "lnkd.in" in ref:
            return "LinkedIn"
        elif "reddit" in ref:
            return "Reddit"
        elif "twitter" in ref or "t.co" in ref or "x.com" in ref:
            return "Twitter / X"
        elif "github" in ref:
            return "GitHub"
        elif "google" in ref or "bing" in ref or "duckduckgo" in ref:
            return "Direct / Search"
        else:
            return "Other"

    def log_pageview(self, client_ip: str, path: str = "/", referrer: Optional[str] = None):
        """Record a pageview with referrer attribution and unique visitor tracking."""
        today = datetime.now().strftime("%Y-%m-%d")
        ip_hash = self._hash_ip(client_ip)
        source = self._classify_referrer(referrer)

        with self._lock:
            self.total_pageviews += 1
            self.unique_visitors.add(ip_hash)
            
            if today not in self.daily_unique:
                self.daily_unique[today] = set()
            self.daily_unique[today].add(ip_hash)

            self.referrers[source] = self.referrers.get(source, 0) + 1

            # Keep last 50 activity events
            event = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "date": today,
                "type": "pageview",
                "path": path,
                "source": source
            }
            self.recent_activity.insert(0, event)
            if len(self.recent_activity) > 50:
                self.recent_activity.pop()

            self.save_to_disk()

    def log_verification(self, client_ip: str):
        """Record that a fact-checking verification was executed (anonymized, zero claim text stored)."""
        today = datetime.now().strftime("%Y-%m-%d")
        ip_hash = self._hash_ip(client_ip)

        with self._lock:
            self.total_verifications += 1
            self.unique_visitors.add(ip_hash)

            if today not in self.daily_unique:
                self.daily_unique[today] = set()
            self.daily_unique[today].add(ip_hash)

            event = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "date": today,
                "type": "verification",
                "label": "Statement fact-check executed"
            }
            self.recent_activity.insert(0, event)
            if len(self.recent_activity) > 50:
                self.recent_activity.pop()

            self.save_to_disk()

    def get_summary(self) -> Dict[str, Any]:
        """Generate comprehensive analytics summary for /analytics/ and API."""
        with self._lock:
            today = datetime.now().strftime("%Y-%m-%d")
            today_visitors = len(self.daily_unique.get(today, set()))
            total_uniques = len(self.unique_visitors)
            
            conversion_rate = 0.0
            if self.total_pageviews > 0:
                conversion_rate = min(100.0, round((self.total_verifications / self.total_pageviews) * 100, 1))

            # Sort daily visitor trend (last 7 days)
            recent_days = sorted(self.daily_unique.keys())[-7:]
            trend = {d: len(self.daily_unique[d]) for d in recent_days}

            # Sanitize recent activity: strictly ensure no private claim text is ever exposed
            sanitized_activity = []
            for ev in self.recent_activity[:10]:
                item = {k: v for k, v in ev.items() if k != "claim_snippet"}
                if item.get("type") == "verification" and "label" not in item:
                    item["label"] = "Statement fact-check executed"
                sanitized_activity.append(item)

            return {
                "total_pageviews": self.total_pageviews,
                "unique_visitors": total_uniques,
                "today_visitors": today_visitors,
                "total_verifications": self.total_verifications,
                "conversion_rate_pct": conversion_rate,
                "traffic_sources": dict(self.referrers),
                "visitor_trend_7d": trend,
                "recent_activity": sanitized_activity
            }

    def save_to_disk(self):
        """Persist visitor metrics atomically to disk with PID/thread-safe temp files."""
        with self._lock:
            temp_file = None
            try:
                self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "total_pageviews": self.total_pageviews,
                    "total_verifications": self.total_verifications,
                    "unique_visitors": list(self.unique_visitors),
                    "daily_unique": {k: list(v) for k, v in self.daily_unique.items()},
                    "referrers": self.referrers,
                    "recent_activity": self.recent_activity
                }
                temp_file = self.metrics_path.with_suffix(f".tmp_{os.getpid()}_{threading.get_ident()}_{time.time_ns()}")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                temp_file.replace(self.metrics_path)
            except Exception as e:
                logger.error(f"Failed to save visitor metrics: {e}")
                if temp_file and temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass

    def load_from_disk(self):
        """Load visitor metrics from disk."""
        with self._lock:
            try:
                if self.metrics_path.exists():
                    with open(self.metrics_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.total_pageviews = data.get("total_pageviews", 0)
                    self.total_verifications = data.get("total_verifications", 0)
                    self.unique_visitors = set(data.get("unique_visitors", []))
                    self.daily_unique = {k: set(v) for k, v in data.get("daily_unique", {}).items()}
                    self.referrers = data.get("referrers", self.referrers)
                    # Strip any legacy claim_snippets to ensure absolute user privacy
                    raw_activity = data.get("recent_activity", [])
                    cleaned_activity = []
                    for ev in raw_activity:
                        if "claim_snippet" in ev:
                            del ev["claim_snippet"]
                            ev["label"] = "Statement fact-check executed"
                        cleaned_activity.append(ev)
                    self.recent_activity = cleaned_activity
                    logger.info(f"Loaded visitor telemetry: {len(self.unique_visitors)} uniques, {self.total_pageviews} views")
            except Exception as e:
                logger.error(f"Failed to load visitor metrics: {e}")


visitor_tracker = VisitorTracker()

