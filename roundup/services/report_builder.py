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


def build_prompt_inputs(league_name: str, week: int, scoreboard: List[Dict[str, Any]], standings: List[Dict[str, Any]], incentives: Dict[str, Any]) -> Dict[str, Any]:
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
    return {
        "league_name": league_name,
        "week": week,
        "scoreboard": compact_scoreboard,
        "standings_top5": compact_standings,
        "incentives": incentives,
    }
