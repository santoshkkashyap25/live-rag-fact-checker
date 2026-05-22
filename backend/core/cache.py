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
    
    def get_cache_key(self, claim: str) -> str:
        """Generate cache key from claim"""
        return hashlib.md5(claim.lower().strip().encode()).hexdigest()
    
    def get(self, claim: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached result if exists and not expired"""
        key = self.get_cache_key(claim)
        
        if key not in self.cache:
            return None
        
        cached_item = self.cache[key]
        cached_time = datetime.fromisoformat(cached_item['timestamp'])
        
        # Check if expired
        if datetime.now() - cached_time > timedelta(seconds=self.ttl_seconds):
            logger.info(f"Cache expired for key: {key[:8]}...")
            del self.cache[key]
            return None
        
        logger.info(f"Cache hit for key: {key[:8]}...")
        return cached_item['result']
    
    def set(self, claim: str, result: Dict[str, Any]):
        """Cache result with timestamp"""
        key = self.get_cache_key(claim)
        
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
            'claim': claim[:100]  # Store truncated claim for debugging
        }
        logger.info(f"Cached result for key: {key[:8]}...")
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def save_to_disk(self):
        """Persist cache to disk"""
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_PATH, 'w') as f:
                json.dump(self.cache, f, indent=2)
            logger.info(f"Cache saved to {CACHE_PATH}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def load_from_disk(self):
        """Load cache from disk"""
        try:
            if CACHE_PATH.exists():
                with open(CACHE_PATH, 'r') as f:
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