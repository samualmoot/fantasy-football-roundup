"""
Performance monitoring service for tracking app performance metrics.
"""

import time
import logging
from functools import wraps
from django.core.cache import cache
from typing import Callable, Any

logger = logging.getLogger(__name__)


def monitor_performance(func_name: str = None):
    """
    Decorator to monitor function performance and log metrics.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log performance metrics
                logger.info(f"Performance: {func_name or func.__name__} executed in {execution_time:.3f}s")
                
                # Track in cache for analytics
                cache_key = f"perf_{func_name or func.__name__}"
                cache.set(cache_key, execution_time, 3600)  # Cache for 1 hour
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Performance: {func_name or func.__name__} failed after {execution_time:.3f}s: {e}")
                raise
                
        return wrapper
    return decorator


def track_cache_hit(cache_key: str, hit: bool):
    """
    Track cache hit/miss rates for performance analysis.
    """
    hit_key = f"cache_hit_{cache_key}"
    miss_key = f"cache_miss_{cache_key}"
    
    if hit:
        cache.incr(hit_key, 1)
    else:
        cache.incr(miss_key, 1)
    
    # Set expiration if keys don't exist
    if not cache.get(hit_key):
        cache.set(hit_key, 1, 3600)
    if not cache.get(miss_key):
        cache.set(miss_key, 1, 3600)


def get_performance_stats():
    """
    Get current performance statistics from cache.
    """
    stats = {}
    
    # Get cache hit rates
    cache_keys = cache.keys("cache_*")
    for key in cache_keys:
        if key.startswith("cache_hit_"):
            hit_count = cache.get(key, 0)
            miss_key = key.replace("cache_hit_", "cache_miss_")
            miss_count = cache.get(miss_key, 0)
            total = hit_count + miss_count
            
            if total > 0:
                hit_rate = (hit_count / total) * 100
                stats[key] = {
                    "hits": hit_count,
                    "misses": miss_count,
                    "hit_rate": f"{hit_rate:.1f}%"
                }
    
    # Get performance times
    perf_keys = cache.keys("perf_*")
    for key in perf_keys:
        execution_time = cache.get(key, 0)
        stats[key] = f"{execution_time:.3f}s"
    
    return stats


def log_page_load_time(page_name: str, load_time: float):
    """
    Log page load times for performance tracking.
    """
    logger.info(f"Page Load: {page_name} loaded in {load_time:.3f}s")
    
    # Store in cache for analytics
    cache_key = f"page_load_{page_name}"
    cache.set(cache_key, load_time, 3600)
