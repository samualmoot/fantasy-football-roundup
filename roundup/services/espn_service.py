from typing import List, Dict, Any
from espn_api.football import League
import functools

# Cache for box scores to avoid repeated API calls
_box_score_cache = {}

def _get_cached_box_scores(league: League, week: int) -> List:
    """Get box scores with caching to avoid repeated API calls."""
    cache_key = f"{league.league_id}_{league.year}_{week}"
    if cache_key not in _box_score_cache:
        try:
            _box_score_cache[cache_key] = league.box_scores(week)
        except Exception:
            _box_score_cache[cache_key] = []
    return _box_score_cache[cache_key]

def get_scoreboard(league: League, week: int) -> List[Dict[str, Any]]:
    """
    Return a list of matchups with team names, scores, and logos for the given week.
    If one side's score is 0 while the other is > 0, treat that side as a BYE.
    """
    matchups = []
    box_scores = _get_cached_box_scores(league, week)

    for b in box_scores:
        home_team_obj = getattr(b, "home_team", None)
        away_team_obj = getattr(b, "away_team", None)
        home_id = getattr(home_team_obj, "team_id", None)
        away_id = getattr(away_team_obj, "team_id", None)
        home_name = getattr(home_team_obj, "team_name", str(home_id if home_id is not None else "Home"))
        away_name = getattr(away_team_obj, "team_name", str(away_id if away_id is not None else "Away"))
        home_logo = getattr(home_team_obj, "logo_url", None)
        away_logo = getattr(away_team_obj, "logo_url", None)
        home_score = getattr(b, "home_score", 0.0)
        away_score = getattr(b, "away_score", 0.0)

        # Bye labeling: if one side has 0 and the other > 0, the 0 side is 'Bye'
        try:
            hs = float(home_score)
            as_ = float(away_score)
        except (TypeError, ValueError):
            hs = 0.0
            as_ = 0.0
        if hs == 0.0 and as_ > 0.0:
            home_name = "Bye"
            home_logo = None
            home_id = None
        elif as_ == 0.0 and hs > 0.0:
            away_name = "Bye"
            away_logo = None
            away_id = None

        diff = (hs - as_) if isinstance(hs, (int, float)) and isinstance(as_, (int, float)) else 0.0
        matchups.append({
            "home_id": home_id,
            "away_id": away_id,
            "home_team": home_name,
            "away_team": away_name,
            "home_logo": home_logo,
            "away_logo": away_logo,
            "home_score": hs,
            "away_score": as_,
            "margin": abs(diff),
            "winner": home_name if diff > 0 else (away_name if diff < 0 else None),
        })
    return matchups


def _compute_standings_through_week(league: League, through_week: int) -> List[Dict[str, Any]]:
    """Compute standings up to and including through_week using box scores.
    Tie-breaker: wins desc, points_for desc.
    """
    # Initialize team map
    team_stats: Dict[int, Dict[str, Any]] = {}
    for t in league.teams:
        abbrev = getattr(t, "team_abbrev", getattr(t, "abbrev", None))
        logo_url = getattr(t, "logo_url", None)
        team_stats[t.team_id] = {
            "team_id": t.team_id,
            "team_name": t.team_name,
            "team_abbrev": abbrev,
            "logo_url": logo_url,
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "points_for": 0.0,
            "points_against": 0.0,
        }

    for wk in range(1, max(1, through_week) + 1):
        boxes = _get_cached_box_scores(league, wk)
        for b in boxes:
            ht = getattr(b, "home_team", None)
            at = getattr(b, "away_team", None)
            if ht is None or at is None:
                continue
            hid = getattr(ht, "team_id", None)
            aid = getattr(at, "team_id", None)
            hs = float(getattr(b, "home_score", 0.0) or 0.0)
            as_ = float(getattr(b, "away_score", 0.0) or 0.0)

            # Aggregate points
            if hid in team_stats:
                team_stats[hid]["points_for"] += hs
                team_stats[hid]["points_against"] += as_
            if aid in team_stats:
                team_stats[aid]["points_for"] += as_
                team_stats[aid]["points_against"] += hs

            # Record results (ignore byes: both zero)
            if hs == 0.0 and as_ == 0.0:
                continue
            if hs > as_:
                if hid in team_stats:
                    team_stats[hid]["wins"] += 1
                if aid in team_stats:
                    team_stats[aid]["losses"] += 1
            elif as_ > hs:
                if aid in team_stats:
                    team_stats[aid]["wins"] += 1
                if hid in team_stats:
                    team_stats[hid]["losses"] += 1
            else:
                if hid in team_stats:
                    team_stats[hid]["ties"] += 1
                if aid in team_stats:
                    team_stats[aid]["ties"] += 1

    standings = list(team_stats.values())
    # Round PF to one decimal
    for s in standings:
        try:
            s["points_for"] = round(float(s["points_for"]), 1)
        except Exception:
            s["points_for"] = 0.0
    standings.sort(key=lambda x: (x["wins"], x["points_for"]), reverse=True)
    # Attach rank (1-based)
    for idx, s in enumerate(standings, start=1):
        s["rank"] = idx
    return standings


def _format_record(wins: int, losses: int, ties: int) -> str:
    if ties and ties > 0:
        return f"{wins}-{losses}-{ties}"
    return f"{wins}-{losses}"


def _build_team_id_to_record(standings: List[Dict[str, Any]]) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    for s in standings:
        tid = s.get("team_id")
        if isinstance(tid, int):
            mapping[tid] = _format_record(int(s.get("wins", 0)), int(s.get("losses", 0)), int(s.get("ties", 0)))
    return mapping


def get_standings_with_movement(league: League, week: int) -> List[Dict[str, Any]]:
    """Return current standings and movement delta vs previous week.
    movement > 0 means moved up that many places; < 0 moved down; None for week 1.
    Adds helper fields: movement_is_up (bool) and movement_abs (int) for templates.
    """
    current = _compute_standings_through_week(league, week)
    if week <= 1:
        for s in current:
            s["movement"] = None
            s["movement_is_up"] = None
            s["movement_abs"] = None
        return current

    previous = _compute_standings_through_week(league, week - 1)
    prev_rank_by_id = {s["team_id"]: s["rank"] for s in previous}
    for s in current:
        prev_rank = prev_rank_by_id.get(s["team_id"])  # may be None early season
        if prev_rank is None:
            s["movement"] = None
            s["movement_is_up"] = None
            s["movement_abs"] = None
        else:
            # Positive movement means improved rank (lower rank number)
            delta = prev_rank - s["rank"]
            s["movement"] = delta if delta != 0 else 0
            if delta == 0:
                s["movement_is_up"] = None
                s["movement_abs"] = 0
            else:
                s["movement_is_up"] = delta > 0
                s["movement_abs"] = abs(delta)
    return current


def get_top_players(league: League, week: int, top_n: int = 3) -> List[Dict[str, Any]]:
    """Return top-N NFL player fantasy scorers for the given week across all teams.
    Bench/IR players are ignored when detectable via slot_position.
    """
    players: List[Dict[str, Any]] = []
    box_scores = _get_cached_box_scores(league, week)

    def add_lineup(lineup, fantasy_team_name: str):
        for pl in lineup or []:
            try:
                points = float(getattr(pl, "points", 0.0) or 0.0)
            except Exception:
                points = 0.0
            slot = getattr(pl, "slot_position", None)
            # Exclude bench/IR if known
            if isinstance(slot, str) and slot.upper() in {"BE", "IR", "IR-R", "OUT", "RES"}:
                continue
            name = getattr(pl, "name", getattr(pl, "playerName", "Player"))
            position = getattr(pl, "position", None)
            nfl_team = getattr(pl, "proTeam", getattr(pl, "proTeamAbbreviation", None))
            players.append({
                "player_name": name,
                "position": position,
                "nfl_team": nfl_team,
                "points": round(points, 1),
                "fantasy_team": fantasy_team_name,
            })

    for b in box_scores:
        home_team_obj = getattr(b, "home_team", None)
        away_team_obj = getattr(b, "away_team", None)
        home_name = getattr(home_team_obj, "team_name", str(getattr(home_team_obj, "team_id", "Home")))
        away_name = getattr(away_team_obj, "team_name", str(getattr(away_team_obj, "team_id", "Away")))
        add_lineup(getattr(b, "home_lineup", []), home_name)
        add_lineup(getattr(b, "away_lineup", []), away_name)

    players.sort(key=lambda x: x.get("points", 0.0), reverse=True)
    return players[:max(0, top_n)]


def get_all_player_performances(league: League, week: int) -> List[Dict[str, Any]]:
    """Return all player performances for the week with starter/bench flag.

    Each entry: player_name, position, nfl_team, points, fantasy_team, is_bench (bool)
    """
    players: List[Dict[str, Any]] = []
    box_scores = _get_cached_box_scores(league, week)

    def add_lineup(lineup, fantasy_team_name: str):
        for pl in lineup or []:
            try:
                points = float(getattr(pl, "points", 0.0) or 0.0)
            except Exception:
                points = 0.0
            slot = getattr(pl, "slot_position", None)
            # Treat bench/IR as bench
            is_bench = isinstance(slot, str) and slot.upper() in {"BE", "IR", "IR-R", "OUT", "RES"}
            name = getattr(pl, "name", getattr(pl, "playerName", "Player"))
            position = getattr(pl, "position", None)
            nfl_team = getattr(pl, "proTeam", getattr(pl, "proTeamAbbreviation", None))
            players.append({
                "player_name": name,
                "position": position,
                "nfl_team": nfl_team,
                "points": round(points, 1),
                "fantasy_team": fantasy_team_name,
                "is_bench": is_bench,
            })

    for b in box_scores:
        home_team_obj = getattr(b, "home_team", None)
        away_team_obj = getattr(b, "away_team", None)
        home_name = getattr(home_team_obj, "team_name", str(getattr(home_team_obj, "team_id", "Home")))
        away_name = getattr(away_team_obj, "team_name", str(getattr(away_team_obj, "team_id", "Away")))
        add_lineup(getattr(b, "home_lineup", []), home_name)
        add_lineup(getattr(b, "away_lineup", []), away_name)

    return players


def compute_position_leaders(
    performances: List[Dict[str, Any]],
    *,
    top_n: int = 1,
    bottom_n: int = 1,
    include_positions: List[str] | None = None,
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Compute best and worst starters by position.

    Returns mapping like:
      {
        'QB': { 'best': [..top_n..], 'busts': [..bottom_n..] },
        ...
      }
    """
    # Normalize desired positions
    desired = include_positions or ["QB", "RB", "WR", "TE", "K", "DEF"]

    def norm_pos(p: Any) -> str | None:
        if not p:
            return None
        s = str(p).upper().strip()
        if s in {"DEF", "DST", "D/ST", "D-ST", "D ST"}:
            return "DEF"
        if s in {"QB", "RB", "WR", "TE", "K"}:
            return s
        return None

    # Group starters by normalized position
    grouped: Dict[str, List[Dict[str, Any]]] = {pos: [] for pos in desired}
    for pl in performances:
        if pl.get("is_bench"):
            continue
        pos = norm_pos(pl.get("position"))
        if pos and pos in grouped:
            grouped[pos].append(pl)

    leaders: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for pos in desired:
        lst = grouped.get(pos, [])
        # Sort copies to avoid mutating original
        best = sorted(lst, key=lambda x: x.get("points", 0.0), reverse=True)[: max(0, top_n)]
        busts = sorted(lst, key=lambda x: x.get("points", 0.0))[: max(0, bottom_n)]
        leaders[pos] = {"best": best, "busts": busts}

    return leaders

# Function to clear cache if needed
def clear_box_score_cache():
    """Clear the box score cache. Useful for testing or when data might be stale."""
    global _box_score_cache
    _box_score_cache = {}


def get_bottom_players(league: League, week: int, bottom_n: int = 3) -> List[Dict[str, Any]]:
    """Return bottom-N scoring starters for the given week across all teams.
    Bench/IR are excluded when detectable via slot_position. Sorted ascending by points.
    """
    players: List[Dict[str, Any]] = []
    box_scores = _get_cached_box_scores(league, week)

    def add_lineup(lineup, fantasy_team_name: str):
        for pl in lineup or []:
            try:
                points = float(getattr(pl, "points", 0.0) or 0.0)
            except Exception:
                points = 0.0
            slot = getattr(pl, "slot_position", None)
            # Exclude bench/IR if known
            if isinstance(slot, str) and slot.upper() in {"BE", "IR", "IR-R", "OUT", "RES"}:
                continue
            name = getattr(pl, "name", getattr(pl, "playerName", "Player"))
            position = getattr(pl, "position", None)
            nfl_team = getattr(pl, "proTeam", getattr(pl, "proTeamAbbreviation", None))
            players.append({
                "player_name": name,
                "position": position,
                "nfl_team": nfl_team,
                "points": round(points, 1),
                "fantasy_team": fantasy_team_name,
            })

    for b in box_scores:
        home_team_obj = getattr(b, "home_team", None)
        away_team_obj = getattr(b, "away_team", None)
        home_name = getattr(home_team_obj, "team_name", str(getattr(home_team_obj, "team_id", "Home")))
        away_name = getattr(away_team_obj, "team_name", str(getattr(away_team_obj, "team_id", "Away")))
        add_lineup(getattr(b, "home_lineup", []), home_name)
        add_lineup(getattr(b, "away_lineup", []), away_name)

    players.sort(key=lambda x: x.get("points", 0.0))
    return players[:max(0, bottom_n)]


def get_previous_standings(league: League, week: int) -> List[Dict[str, Any]]:
    """Return standings through week-1 (empty for week <= 1)."""
    if week <= 1:
        return []
    return _compute_standings_through_week(league, week - 1)
