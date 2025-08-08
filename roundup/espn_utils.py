import os
from datetime import datetime
from espn_api.football import League


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
