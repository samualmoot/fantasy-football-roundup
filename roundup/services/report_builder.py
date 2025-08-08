from typing import Dict, Any, List


def compute_incentives(scoreboard: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not scoreboard:
        return {
            "highest_score": None,
            "closest_game": None,
            "biggest_blowout": None,
        }
    highest = max(scoreboard, key=lambda m: max(m["home_score"], m["away_score"]))
    closest = min(scoreboard, key=lambda m: m["margin"]) if len(scoreboard) > 0 else None
    blowout = max(scoreboard, key=lambda m: m["margin"]) if len(scoreboard) > 0 else None

    def describe(match):
        if not match:
            return None
        winner = match.get("winner")
        loser = match["home_team"] if winner == match.get("away_team") else match["away_team"]
        win_score = max(match["home_score"], match["away_score"])
        lose_score = min(match["home_score"], match["away_score"])
        return {
            "winner": winner,
            "loser": loser,
            "winner_score": win_score,
            "loser_score": lose_score,
            "margin": match["margin"],
        }

    return {
        "highest_score": describe(highest),
        "closest_game": describe(closest),
        "biggest_blowout": describe(blowout),
    }


def build_prompt_inputs(
    league_name: str,
    week: int,
    scoreboard: List[Dict[str, Any]],
    standings: List[Dict[str, Any]],
    incentives: Dict[str, Any],
    top_players: List[Dict[str, Any]] | None = None,
    previous_standings: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    # Keep inputs compact; include top-5 standings only
    compact_standings = standings[:5]
    compact_scoreboard = [
        {
            "home": m["home_team"],
            "away": m["away_team"],
            "home_score": m["home_score"],
            "away_score": m["away_score"],
            "winner": m["winner"],
        }
        for m in scoreboard
    ]
    # Derived facts for a better overview
    close_games = [
        {
            "home": m["home_team"],
            "away": m["away_team"],
            "margin": m.get("margin", 0.0),
            "winner": m.get("winner"),
        }
        for m in scoreboard
        if (m.get("margin") is not None) and m.get("margin", 0.0) < 5.0 and m.get("winner")
    ]
    undefeated = [s["team_name"] for s in compact_standings if s.get("losses", 0) == 0 and s.get("wins", 0) > 0]

    prev_by_id = {s.get("team_id"): s for s in (previous_standings or []) if s.get("team_id") is not None}
    first_wins = []
    for s in standings:
        tid = s.get("team_id")
        prev = prev_by_id.get(tid)
        if prev and prev.get("wins", 0) == 0 and s.get("wins", 0) > 0:
            first_wins.append(s.get("team_name"))

    return {
        "league_name": league_name,
        "week": week,
        "scoreboard": compact_scoreboard,
        "standings_top5": compact_standings,
        "incentives": incentives,
        "top_players": (top_players or [])[:3],
        "close_games": close_games[:3],
        "undefeated_teams": undefeated[:3],
        "first_wins": first_wins[:3],
    }
