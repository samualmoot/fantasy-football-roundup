import os
from datetime import datetime
from espn_api.football import League
import time

# Simple in-process cache for League objects keyed by year
_LEAGUE_CACHE: dict[int, dict] = {}
_LEAGUE_TTL_SECONDS = 600  # 10 minutes


def get_league(year=None):
    """
    Fetches the ESPN fantasy football league object using credentials from environment variables.
    Set ESPN_LEAGUE_ID in .env to override the default.
    """
    league_id_env = os.environ.get('ESPN_LEAGUE_ID')
    try:
        league_id = int(league_id_env) if league_id_env else 1470361165
    except ValueError:
        league_id = 1470361165

    year = year or datetime.now().year
    swid = os.environ.get('ESPN_SWID')
    espn_s2 = os.environ.get('ESPN_S2')
    if not swid or not espn_s2:
        raise ValueError("Missing ESPN_SWID or ESPN_S2 environment variables.")
    league = League(league_id=league_id, year=year, swid=swid, espn_s2=espn_s2)
    return league


def get_league_cached(year=None):
    """
    Return a memoized League object for the given year with a short TTL to avoid
    repeated ESPN authentication and metadata fetches.
    """
    y = year or datetime.now().year
    swid = os.environ.get('ESPN_SWID')
    espn_s2 = os.environ.get('ESPN_S2')
    league_id_env = os.environ.get('ESPN_LEAGUE_ID')
    try:
        league_id = int(league_id_env) if league_id_env else 1470361165
    except ValueError:
        league_id = 1470361165

    if not swid or not espn_s2:
        raise ValueError("Missing ESPN_SWID or ESPN_S2 environment variables.")

    now = time.time()
    entry = _LEAGUE_CACHE.get(y)
    if entry:
        if (
            now - entry.get("ts", 0) < _LEAGUE_TTL_SECONDS
            and entry.get("swid") == swid
            and entry.get("espn_s2") == espn_s2
            and entry.get("league_id") == league_id
        ):
            league_obj = entry.get("league")
            if league_obj is not None:
                return league_obj

    league = League(league_id=league_id, year=y, swid=swid, espn_s2=espn_s2)
    _LEAGUE_CACHE[y] = {
        "league": league,
        "ts": now,
        "swid": swid,
        "espn_s2": espn_s2,
        "league_id": league_id,
    }
    return league


def get_playoff_team_count(league: League) -> int:
    """Best-effort detection of how many teams make the playoffs.

    Tries common attribute names on `league.settings` used by ESPN and espn-api.
    Falls back to a sensible default (6) clamped to the number of teams.
    """
    default_count = 6
    settings = getattr(league, "settings", None)
    if settings is not None:
        # Try a handful of likely attribute names first (snake_case and camelCase)
        candidate_attr_names = (
            "playoff_team_count",
            "playoffTeamCount",
            "num_playoff_teams",
            "numPlayoffTeams",
        )
        for name in candidate_attr_names:
            try:
                value = getattr(settings, name, None)
                if isinstance(value, int) and value > 0:
                    return value
            except Exception:
                pass

        # Heuristic: search any attribute that looks like it might match
        try:
            for key, value in vars(settings).items():
                if not isinstance(key, str):
                    continue
                lowered = key.lower()
                if "playoff" in lowered and "team" in lowered and isinstance(value, int) and 2 <= value <= 20:
                    return value
        except Exception:
            pass

    team_count = len(getattr(league, "teams", []) or [])
    return max(2, min(default_count, team_count or default_count))