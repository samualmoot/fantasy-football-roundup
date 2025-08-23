"""
Simple in-memory cache for production environments.
This provides fast caching without external dependencies.
"""

import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SimpleCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache if it exists and hasn't expired."""
        if key not in self._cache:
            return None
        
        # Check if expired
        if time.time() > self._timestamps[key]:
            # Clean up expired entry
            del self._cache[key]
            del self._timestamps[key]
            return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any, timeout: int = 3600) -> None:
        """Set a value in cache with TTL."""
        self._cache[key] = value
        self._timestamps[key] = time.time() + timeout
    
    def delete(self, key: str) -> None:
        """Delete a key from cache."""
        if key in self._cache:
            del self._cache[key]
        if key in self._timestamps:
            del self._timestamps[key]
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._timestamps.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)

# Global cache instance
_simple_cache = SimpleCache()

def get_cached_data(key: str) -> Optional[Any]:
    """Get data from simple cache."""
    return _simple_cache.get(key)

def set_cached_data(key: str, value: Any, timeout: int = 3600) -> None:
    """Set data in simple cache."""
    _simple_cache.set(key, value, timeout)

def clear_cache() -> None:
    """Clear the simple cache."""
    _simple_cache.clear()

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return {
        "cache_type": "Simple In-Memory Cache",
        "size": _simple_cache.size(),
        "status": "Working"
    }
