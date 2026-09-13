# core/cache.py
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import logging
from config import CACHE_PATH, CACHE_MAX_SIZE, CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)

class QueryCache:
    """LRU cache with TTL for query results"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = CACHE_MAX_SIZE
        self.ttl_seconds = CACHE_TTL_SECONDS
        self.load_from_disk()
    
    def get_cache_key(self, claim: str, user_id: str = "default") -> str:
        """Generate cache key from claim and user_id"""
        clean_user = (user_id or "default").strip()
        clean_claim = claim.lower().strip()
        return hashlib.md5(f"{clean_user}:{clean_claim}".encode()).hexdigest()
    
    def get(self, claim: str, user_id: str = "default") -> Optional[Dict[str, Any]]:
        """Retrieve cached result if exists and not expired for the given user"""
        key = self.get_cache_key(claim, user_id)
        
        if key not in self.cache:
            return None
        
        cached_item = self.cache[key]
        cached_time = datetime.fromisoformat(cached_item['timestamp'])
        
        # Check if expired
        if datetime.now() - cached_time > timedelta(seconds=self.ttl_seconds):
            logger.info(f"Cache expired for user '{user_id}' key: {key[:8]}...")
            del self.cache[key]
            return None
        
        logger.info(f"Cache hit for user '{user_id}' key: {key[:8]}...")
        return cached_item['result']
    
    def set(self, claim: str, result: Dict[str, Any], user_id: str = "default"):
        """Cache result with timestamp and user attribution"""
        key = self.get_cache_key(claim, user_id)
        
        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size:
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k]['timestamp']
            )
            del self.cache[oldest_key]
            logger.info(f"Evicted oldest cache entry: {oldest_key[:8]}...")
        
        self.cache[key] = {
            'result': result,
            'timestamp': datetime.now().isoformat(),
            'claim': claim[:100],  # Store truncated claim for debugging
            'user_id': user_id or "default"
        }
        logger.info(f"Cached result for user '{user_id}' key: {key[:8]}...")
        self.save_to_disk()
    
    def clear(self, user_id: Optional[str] = None):
        """Clear cache for a specific user, or all cache if user_id is None"""
        if user_id:
            clean_user = user_id.strip()
            keys_to_delete = [
                k for k, v in self.cache.items()
                if v.get('user_id') == clean_user or k == self.get_cache_key(v.get('claim', ''), clean_user)
            ]
            for k in keys_to_delete:
                del self.cache[k]
            logger.info(f"Cache cleared for user '{clean_user}' ({len(keys_to_delete)} entries removed)")
        else:
            self.cache.clear()
            logger.info("All cache entries cleared")
        self.save_to_disk()
    
    def save_to_disk(self):
        """Persist cache to disk"""
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
            logger.info(f"Cache saved to {CACHE_PATH}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def load_from_disk(self):
        """Load cache from disk"""
        try:
            if CACHE_PATH.exists():
                with open(CACHE_PATH, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"Cache loaded from {CACHE_PATH} ({len(self.cache)} entries)")
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            self.cache = {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds
        }

query_cache = QueryCache()