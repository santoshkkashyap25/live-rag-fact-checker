# core/share_store.py
import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import re
from core.security import sanitize_secrets

logger = logging.getLogger(__name__)

SHARE_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "shared_verdicts.json"

class ShareStore:
    """Persistent storage for shareable fact-checking verdicts"""

    def __init__(self, store_path: Path = SHARE_STORE_PATH):
        self.store_path = store_path
        self.store: Dict[str, Dict[str, Any]] = {}
        self.load_from_disk()

    def load_from_disk(self):
        """Load stored verdicts from JSON file"""
        try:
            if self.store_path.exists():
                with open(self.store_path, "r", encoding="utf-8") as f:
                    self.store = json.load(f)
                logger.info(f"Loaded {len(self.store)} shared verdicts from {self.store_path}")
            else:
                self.store = {}
        except Exception as e:
            logger.error(f"Error loading shared verdicts from {self.store_path}: {e}")
            self.store = {}

    def save_to_disk(self):
        """Persist stored verdicts atomically to JSON file"""
        temp_file = None
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self.store_path.with_suffix(f".tmp_{time.time_ns()}")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.store, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.store_path)
            logger.info(f"Saved {len(self.store)} shared verdicts to {self.store_path}")
        except Exception as e:
            logger.error(f"Failed to persist shared verdicts to {self.store_path}: {e}")
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

    def generate_short_id(self, claim: str, verdict: str) -> str:
        """Generate a clean, collision-resistant 6-character hex ID"""
        raw = f"{claim}:{verdict}:{time.time()}"
        full_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        short_id = full_hash[:6]
        # Handle collision if any
        counter = 1
        while short_id in self.store and counter < 10:
            short_id = full_hash[counter:counter+6]
            counter += 1
        return short_id

    def save_verdict(self, result: Dict[str, Any]) -> str:
        """Store verification result with strict field whitelisting and zero credential leakage"""
        claim = sanitize_secrets(result.get("extracted_claim") or result.get("input_text") or "Claim")[:250]
        raw_verdict = str(result.get("verdict", "Unverifiable"))[:20]
        verdict = raw_verdict if raw_verdict in ["True", "False", "Unverifiable"] else "Unverifiable"

        # Check if already stored recently with identical claim and verdict
        clean_claim = claim.strip().lower()
        for sid, item in self.store.items():
            stored_claim = (item.get("extracted_claim") or item.get("input_text") or "").strip().lower()
            if stored_claim == clean_claim and item.get("verdict") == verdict:
                return sid

        short_id = self.generate_short_id(claim, verdict)
        
        # Whitelist engine & performance fields strictly
        raw_engine = result.get("engine", {})
        safe_engine = {
            "provider": sanitize_secrets(str(raw_engine.get("provider", "groq"))[:30]),
            "model": sanitize_secrets(str(raw_engine.get("model", "default"))[:60])
        }

        raw_perf = result.get("performance", {})
        safe_perf = {
            "extraction_time": str(raw_perf.get("extraction_time", "0.00s"))[:15],
            "retrieval_time": str(raw_perf.get("retrieval_time", "0.00s"))[:15],
            "llm_time": str(raw_perf.get("llm_time", "0.00s"))[:15],
            "total_time": str(raw_perf.get("total_time", "0.00s"))[:15]
        }

        safe_evidence = [sanitize_secrets(e)[:1000] for e in result.get("evidence", [])[:10]]
        safe_scores = [str(s)[:10] for s in result.get("evidence_scores", [])[:10]]
        safe_sources = [sanitize_secrets(s)[:60] for s in result.get("evidence_sources", [])[:10]]
        safe_urls = [str(u)[:300] for u in result.get("evidence_urls", [])[:10] if isinstance(u, str) and u.startswith("http")]

        self.store[short_id] = {
            "id": short_id,
            "input_text": sanitize_secrets(result.get("input_text", ""))[:1000],
            "extracted_claim": claim,
            "verdict": verdict,
            "confidence": result.get("confidence", 0.9),
            "reasoning": sanitize_secrets(result.get("reasoning", ""))[:2000],
            "evidence": safe_evidence,
            "evidence_scores": safe_scores,
            "evidence_sources": safe_sources,
            "evidence_urls": safe_urls,
            "engine": safe_engine,
            "performance": safe_perf,
            "created_at": datetime.now().isoformat()
        }
        self.save_to_disk()
        return short_id

    def get_verdict(self, share_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored verdict by validated short ID"""
        if not share_id:
            return None
        clean_id = share_id.strip()
        if not re.match(r'^[a-zA-Z0-9_\-]{4,16}$', clean_id):
            return None
        return self.store.get(clean_id)

share_store = ShareStore()
