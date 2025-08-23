"""
Team logo management service for performance optimization.
Handles bulk logo operations and caching.
"""

import os
import httpx
from typing import Dict, List, Optional, Tuple
from django.core.cache import cache
from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)


def preload_all_team_logos(teams: List) -> Dict[int, str]:
    """
    Preload all team logos and return a mapping of team_id to logo data.
    This prevents individual API calls for each logo.
    """
    logo_cache = {}
    
    for team in teams:
        team_id = getattr(team, "team_id", None)
        if not team_id:
            continue
            
        # Check if already cached
        cache_key = f"team_logo_{team_id}"
        cached_logo = cache.get(cache_key)
        
        if cached_logo:
            logo_cache[team_id] = cached_logo
            continue
            
        # Fetch and cache logo
        logo_data = _fetch_team_logo(team)
        if logo_data:
            logo_cache[team_id] = logo_data
            cache.set(cache_key, logo_data, 86400)  # 24 hours
    
    return logo_cache


def _fetch_team_logo(team) -> Optional[str]:
    """Fetch a single team logo and return the data URL or None."""
    logo_url = getattr(team, "logo_url", None)
    if not logo_url:
        return None
        
    swid = os.environ.get("ESPN_SWID")
    espn_s2 = os.environ.get("ESPN_S2")
    
    try:
        with httpx.Client(follow_redirects=True, timeout=5.0) as client:
            resp = client.get(
                logo_url, 
                headers={"User-Agent": "Mozilla/5.0"}, 
                cookies={"SWID": swid or "", "espn_s2": espn_s2 or ""}
            )
            if resp.status_code == 200 and resp.content:
                content_type = resp.headers.get("content-type", "image/png")
                # Convert to data URL for inline use
                import base64
                encoded = base64.b64encode(resp.content).decode('utf-8')
                return f"data:{content_type};base64,{encoded}"
    except Exception as e:
        logger.warning(f"Failed to fetch logo for team {getattr(team, 'team_id', 'unknown')}: {e}")
    
    return None


def get_team_logo_data_url(team_id: int, teams: List) -> Optional[str]:
    """
    Get a team logo as a data URL, using cache if available.
    Returns None if logo not found.
    """
    cache_key = f"team_logo_{team_id}"
    cached_logo = cache.get(cache_key)
    
    if cached_logo:
        return cached_logo
        
    # Find team and fetch logo
    team = next((t for t in teams if getattr(t, "team_id", None) == team_id), None)
    if team:
        logo_data = _fetch_team_logo(team)
        if logo_data:
            cache.set(cache_key, logo_data, 86400)
            return logo_data
    
    return None


def bulk_preload_logos_for_context(teams: List) -> Dict[int, str]:
    """
    Preload all logos for a given context (e.g., homepage, report page).
    Returns mapping of team_id to logo data URLs.
    """
    return preload_all_team_logos(teams)


def clear_logo_cache():
    """Clear all cached team logos. Useful for debugging or force refresh."""
    # This is a simple approach - in production you might want more granular control
    cache.clear()
    logger.info("Team logo cache cleared")
