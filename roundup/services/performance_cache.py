"""
Performance caching service for expensive ESPN API calls and computations.
This service caches data that doesn't change frequently to improve page load times.
"""

import hashlib
import json
from typing import Dict, List, Any, Optional
from django.core.cache import cache
from espn_api.football import League
import logging

logger = logging.getLogger(__name__)

# Cache timeouts
SCOREBOARD_CACHE_TIMEOUT = 3600  # 1 hour
STANDINGS_CACHE_TIMEOUT = 3600   # 1 hour
BOX_SCORES_CACHE_TIMEOUT = 3600  # 1 hour
PLAYER_PERFORMANCES_CACHE_TIMEOUT = 1800  # 30 minutes
INCENTIVES_CACHE_TIMEOUT = 1800  # 30 minutes


def get_cached_scoreboard(league: League, week: int) -> Optional[List[Dict[str, Any]]]:
    """Get cached scoreboard data or return None if not cached."""
    try:
        cache_key = f"scoreboard_{league.league_id}_{league.year}_{week}"
        return cache.get(cache_key)
    except Exception as e:
        logger.warning(f"Cache error getting scoreboard: {e}")
        return None


def cache_scoreboard(league: League, week: int, scoreboard_data: List[Dict[str, Any]]) -> None:
    """Cache scoreboard data."""
    try:
        cache_key = f"scoreboard_{league.league_id}_{league.year}_{week}"
        cache.set(cache_key, scoreboard_data, SCOREBOARD_CACHE_TIMEOUT)
        logger.info(f"Cached scoreboard for league {league.league_id}, year {league.year}, week {week}")
    except Exception as e:
        logger.warning(f"Cache error setting scoreboard: {e}")


def get_cached_standings(league: League, week: int) -> Optional[List[Dict[str, Any]]]:
    """Get cached standings data or return None if not cached."""
    cache_key = f"standings_{league.league_id}_{league.year}_{week}"
    return cache.get(cache_key)


def cache_standings(league: League, week: int, standings_data: List[Dict[str, Any]]) -> None:
    """Cache standings data."""
    cache_key = f"standings_{league.league_id}_{league.year}_{week}"
    cache.set(cache_key, standings_data, STANDINGS_CACHE_TIMEOUT)
    logger.info(f"Cached standings for league {league.league_id}, year {league.year}, week {week}")


def get_cached_box_scores(league: League, week: int) -> Optional[List]:
    """Get cached box scores or return None if not cached."""
    cache_key = f"box_scores_{league.league_id}_{league.year}_{week}"
    return cache.get(cache_key)


def cache_box_scores(league: League, week: int, box_scores: List) -> None:
    """Cache box scores data."""
    cache_key = f"box_scores_{league.league_id}_{league.year}_{week}"
    cache.set(cache_key, box_scores, BOX_SCORES_CACHE_TIMEOUT)
    logger.info(f"Cached box scores for league {league.league_id}, year {league.year}, week {week}")


def get_cached_player_performances(league: League, week: int) -> Optional[List[Dict[str, Any]]]:
    """Get cached player performances or return None if not cached."""
    cache_key = f"player_performances_{league.league_id}_{league.year}_{week}"
    return cache.get(cache_key)


def cache_player_performances(league: League, week: int, performances: List[Dict[str, Any]]) -> None:
    """Cache player performances data."""
    cache_key = f"player_performances_{league.league_id}_{league.year}_{week}"
    cache.set(cache_key, performances, PLAYER_PERFORMANCES_CACHE_TIMEOUT)
    logger.info(f"Cached player performances for league {league.league_id}, year {league.year}, week {week}")


def get_cached_incentives(league: League, week: int) -> Optional[Dict[str, Any]]:
    """Get cached incentives data or return None if not cached."""
    cache_key = f"incentives_{league.league_id}_{league.year}_{week}"
    return cache.get(cache_key)


def cache_incentives(league: League, week: int, incentives_data: Dict[str, Any]) -> None:
    """Cache incentives data."""
    cache_key = f"incentives_{league.league_id}_{league.year}_{week}"
    cache.set(cache_key, incentives_data, INCENTIVES_CACHE_TIMEOUT)
    logger.info(f"Cached incentives for league {league.league_id}, year {league.year}, week {week}")


def get_cached_position_leaders(league: League, week: int) -> Optional[Dict[str, Any]]:
    """Get cached position leaders data or return None if not cached."""
    cache_key = f"position_leaders_{league.league_id}_{league.year}_{week}"
    return cache.get(cache_key)


def cache_position_leaders(league: League, week: int, leaders_data: Dict[str, Any]) -> None:
    """Cache position leaders data."""
    cache_key = f"position_leaders_{league.league_id}_{league.year}_{week}"
    cache.set(cache_key, leaders_data, PLAYER_PERFORMANCES_CACHE_TIMEOUT)
    logger.info(f"Cached position leaders for league {league.league_id}, year {league.year}, week {week}")


def get_cached_weekly_awards(league: League, week: int) -> Optional[List[Dict[str, str]]]:
    """Get cached weekly awards or return None if not cached."""
    cache_key = f"weekly_awards_{league.league_id}_{league.year}_{week}"
    return cache.get(cache_key)


def cache_weekly_awards(league: League, week: int, awards_data: List[Dict[str, str]]) -> None:
    """Cache weekly awards data."""
    cache_key = f"weekly_awards_{league.league_id}_{league.year}_{week}"
    cache.set(cache_key, awards_data, PLAYER_PERFORMANCES_CACHE_TIMEOUT)
    logger.info(f"Cached weekly awards for league {league.league_id}, year {league.year}, week {week}")


def clear_week_cache(league: League, week: int) -> None:
    """Clear all cached data for a specific week."""
    cache_keys = [
        f"scoreboard_{league.league_id}_{league.year}_{week}",
        f"standings_{league.league_id}_{league.year}_{week}",
        f"box_scores_{league.league_id}_{league.year}_{week}",
        f"player_performances_{league.league_id}_{league.year}_{week}",
        f"incentives_{league.league_id}_{league.year}_{week}",
        f"position_leaders_{league.league_id}_{league.year}_{week}",
        f"weekly_awards_{league.league_id}_{league.year}_{week}",
    ]
    
    for key in cache_keys:
        cache.delete(key)
    
    logger.info(f"Cleared all cache for league {league.league_id}, year {league.year}, week {week}")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring."""
    # This is a simple approach - in production you might want more sophisticated monitoring
    stats = {
        "cache_backend": "Django Cache",
        "cache_keys": [],
        "estimated_size": "Unknown"
    }
    
    # Try to get some basic cache info
    try:
        # Test cache functionality
        test_key = "cache_test_key"
        test_value = "test_value"
        cache.set(test_key, test_value, 60)
        retrieved = cache.get(test_key)
        cache.delete(test_key)
        
        if retrieved == test_value:
            stats["cache_status"] = "Working"
        else:
            stats["cache_status"] = "Not Working"
    except Exception as e:
        stats["cache_status"] = f"Error: {str(e)}"
    
    return stats
