# core/share_store.py
import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging

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
        """Persist stored verdicts to JSON file"""
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(self.store, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.store)} shared verdicts to {self.store_path}")
        except Exception as e:
            logger.error(f"Failed to persist shared verdicts to {self.store_path}: {e}")

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
        """Store verification result and return short ID"""
        claim = result.get("extracted_claim") or result.get("input_text") or "Claim"
        verdict = result.get("verdict", "Unverifiable")

        # Check if already stored recently with identical claim and verdict
        clean_claim = claim.strip().lower()
        for sid, item in self.store.items():
            stored_claim = (item.get("extracted_claim") or item.get("input_text") or "").strip().lower()
            if stored_claim == clean_claim and item.get("verdict") == verdict:
                return sid

        short_id = self.generate_short_id(claim, verdict)
        
        self.store[short_id] = {
            "id": short_id,
            "input_text": result.get("input_text", ""),
            "extracted_claim": claim,
            "verdict": verdict,
            "confidence": result.get("confidence", 0.9),
            "reasoning": result.get("reasoning", ""),
            "evidence": result.get("evidence", []),
            "evidence_scores": result.get("evidence_scores", []),
            "evidence_sources": result.get("evidence_sources", []),
            "evidence_urls": result.get("evidence_urls", []),
            "engine": result.get("engine", {"provider": "groq", "model": "default"}),
            "performance": result.get("performance", {}),
            "created_at": datetime.now().isoformat()
        }
        self.save_to_disk()
        return short_id

    def get_verdict(self, share_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored verdict by short ID"""
        clean_id = (share_id or "").strip()
        return self.store.get(clean_id)

share_store = ShareStore()
