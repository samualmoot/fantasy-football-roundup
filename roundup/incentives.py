from __future__ import annotations

from typing import Dict, Any, List, Tuple


# Ordered list of incentive keys. Unique items only.
INCENTIVE_ORDER: List[str] = [
    "highest_team_score",
    "lowest_team_score",
    "closest_game",
    "biggest_blowout",
    "highest_scoring_player_starter",
    "highest_scoring_player_bench",
    "highest_scoring_defense_starter",
    "highest_scoring_qb_starter",
    "highest_scoring_rb_starter",
    "highest_scoring_wr_starter",
    "highest_scoring_te_starter",
    "highest_scoring_k_starter",
    "highest_scoring_flex_starter",
    "highest_team_bench_points",
    "most_20_plus_point_starters",
    "highest_starting_lineup_points",
    "most_10_plus_point_bench_players",
    "most_15_plus_point_starters",
]


INCENTIVE_TITLES: Dict[str, str] = {
    "highest_team_score": "Highest Scoring Team",
    "lowest_team_score": "Lowest Scoring Team",
    "closest_game": "Closest Win",
    "biggest_blowout": "Biggest Blowout",
    "highest_scoring_player_starter": "Highest Scoring Starter",
    "highest_scoring_player_bench": "Highest Scoring Benched Player",
    "highest_scoring_defense_starter": "Highest Scoring Defense (Starter)",
    "highest_scoring_qb_starter": "Highest Scoring QB (Starter)",
    "highest_scoring_rb_starter": "Highest Scoring RB (Starter)",
    "highest_scoring_wr_starter": "Highest Scoring WR (Starter)",
    "highest_scoring_te_starter": "Highest Scoring TE (Starter)",
    "highest_scoring_k_starter": "Highest Scoring K (Starter)",
    "highest_scoring_flex_starter": "Highest Scoring FLEX (RB/WR/TE Starter)",
    "highest_team_bench_points": "Highest Total Bench Points (Team)",
    "most_20_plus_point_starters": "Most 20+ Point Starters (Team)",
    "highest_starting_lineup_points": "Highest Total Starting Lineup Points (Team)",
    "most_10_plus_point_bench_players": "Most 10+ Point Bench Players (Team)",
    "most_15_plus_point_starters": "Most 15+ Point Starters (Team)",
}


def generate_weekly_incentive_schedule(regular_season_weeks: int) -> List[str]:
    """Return a list of incentive keys for each week of the regular season without repeats.

    If the league has more weeks than our catalog, we extend deterministically with
    additional position-specific variants to maintain uniqueness.
    """
    if regular_season_weeks <= len(INCENTIVE_ORDER):
        return INCENTIVE_ORDER[:regular_season_weeks]

    schedule = list(INCENTIVE_ORDER)
    # Deterministic extensions to avoid repeats for long seasons
    extensions: List[str] = [
        "highest_scoring_qb_starter",  # already present; we'll guard against duplicates
        "highest_scoring_rb_starter",
        "highest_scoring_wr_starter",
        "highest_scoring_te_starter",
        "highest_scoring_k_starter",
        "highest_scoring_player_bench",  # bench duplicate guard
        "most_20_plus_point_starters",
        "most_15_plus_point_starters",
        "most_10_plus_point_bench_players",
        "highest_team_bench_points",
        "highest_starting_lineup_points",
    ]
    for key in extensions:
        if key not in schedule:
            schedule.append(key)
        if len(schedule) >= regular_season_weeks:
            return schedule[:regular_season_weeks]
    # If still short, repeat adding no-op placeholders by appending descriptive uniques
    while len(schedule) < regular_season_weeks:
        schedule.append(f"custom_incentive_week_{len(schedule)+1}")
    return schedule[:regular_season_weeks]


def describe_incentive_title(key: str) -> str:
    return INCENTIVE_TITLES.get(key, key.replace("_", " ").title())


def _winner_from_scoreboard_highest(scoreboard: List[Dict[str, Any]]) -> Tuple[str, float] | None:
    best_name = None
    best_score = None
    for m in scoreboard:
        candidates = [
            (m.get("home_team"), m.get("home_score"), m.get("home_id")),
            (m.get("away_team"), m.get("away_score"), m.get("away_id")),
        ]
        for name, score, tid in candidates:
            # Skip BYE and unknown teams (we set id=None for BYE in scoreboard)
            if tid is None:
                continue
            try:
                val = float(score)
            except Exception:
                val = None
            if name and val is not None and (best_score is None or val > best_score):
                best_name, best_score = name, val
    if best_name is None or best_score is None:
        return None
    return best_name, best_score


def _winner_from_scoreboard_lowest(scoreboard: List[Dict[str, Any]]) -> Tuple[str, float] | None:
    worst_name = None
    worst_score = None
    for m in scoreboard:
        candidates = [
            (m.get("home_team"), m.get("home_score"), m.get("home_id")),
            (m.get("away_team"), m.get("away_score"), m.get("away_id")),
        ]
        for name, score, tid in candidates:
            # Skip BYE and unknown teams (we set id=None for BYE in scoreboard)
            if tid is None:
                continue
            try:
                val = float(score)
            except Exception:
                val = None
            if name and val is not None and (worst_score is None or val < worst_score):
                worst_name, worst_score = name, val
    if worst_name is None or worst_score is None:
        return None
    return worst_name, worst_score


def _winner_closest_game(incentives_summary: Dict[str, Any]) -> Tuple[str, float] | None:
    cg = incentives_summary.get("closest_game")
    if not cg:
        return None
    winner = cg.get("winner")
    margin = cg.get("margin")
    if winner is None or margin is None:
        return None
    try:
        return winner, float(margin)
    except Exception:
        return None


def _winner_biggest_blowout(incentives_summary: Dict[str, Any]) -> Tuple[str, float] | None:
    bb = incentives_summary.get("biggest_blowout")
    if not bb:
        return None
    winner = bb.get("winner")
    margin = bb.get("margin")
    if winner is None or margin is None:
        return None
    try:
        return winner, float(margin)
    except Exception:
        return None


def _winner_highest_scoring_player(
    performances: List[Dict[str, Any]], *, starters_only: bool, bench_only: bool,
    position_filter: str | None = None, positions_filter: List[str] | None = None
) -> Tuple[str, float] | None:
    best: Tuple[str, float] | None = None
    for p in performances:
        is_bench = bool(p.get("is_bench"))
        if starters_only and is_bench:
            continue
        if bench_only and not is_bench:
            continue
        pos = p.get("position")
        if position_filter is not None and str(pos).upper() != position_filter.upper():
            continue
        if positions_filter is not None and str(pos).upper() not in {s.upper() for s in positions_filter}:
            continue
        name = p.get("player_name")
        team = p.get("fantasy_team")
        try:
            pts = float(p.get("points", 0.0))
        except Exception:
            pts = 0.0
        label = f"{name} – {pts} for {team}"
        if best is None or pts > best[1]:
            best = (label, pts)
    return best


def compute_incentive_winner(
    key: str,
    *,
    scoreboard: List[Dict[str, Any]],
    incentives_summary: Dict[str, Any],
    performances: List[Dict[str, Any]],
) -> Dict[str, Any]:
    title = describe_incentive_title(key)
    winner_text = ""
    if key == "highest_team_score":
        res = _winner_from_scoreboard_highest(scoreboard)
        if res:
            name, pts = res
            winner_text = f"{name} ({pts})"
    elif key == "lowest_team_score":
        res = _winner_from_scoreboard_lowest(scoreboard)
        if res:
            name, pts = res
            winner_text = f"{name} ({pts})"
    elif key == "closest_game":
        res = _winner_closest_game(incentives_summary)
        if res:
            name, margin = res
            winner_text = f"{name} (won by {margin})"
    elif key == "biggest_blowout":
        res = _winner_biggest_blowout(incentives_summary)
        if res:
            name, margin = res
            winner_text = f"{name} (won by {margin})"
    elif key == "highest_scoring_player_starter":
        res = _winner_highest_scoring_player(performances, starters_only=True, bench_only=False)
        if res:
            label, _ = res
            winner_text = label
    elif key == "highest_scoring_player_bench":
        res = _winner_highest_scoring_player(performances, starters_only=False, bench_only=True)
        if res:
            label, _ = res
            winner_text = label
    elif key == "highest_scoring_defense_starter":
        # ESPN uses D/ST or DST; normalize compare in helper
        # Try both common forms
        res = _winner_highest_scoring_player(performances, starters_only=True, bench_only=False, position_filter="D/ST")
        if res is None:
            res = _winner_highest_scoring_player(performances, starters_only=True, bench_only=False, position_filter="DST")
        if res:
            label, _ = res
            winner_text = label
    elif key == "highest_scoring_qb_starter":
        res = _winner_highest_scoring_player(performances, starters_only=True, bench_only=False, position_filter="QB")
        if res:
            label, _ = res
            winner_text = label
    elif key == "highest_scoring_rb_starter":
        res = _winner_highest_scoring_player(performances, starters_only=True, bench_only=False, position_filter="RB")
        if res:
            label, _ = res
            winner_text = label
    elif key == "highest_scoring_wr_starter":
        res = _winner_highest_scoring_player(performances, starters_only=True, bench_only=False, position_filter="WR")
        if res:
            label, _ = res
            winner_text = label
    elif key == "highest_scoring_te_starter":
        res = _winner_highest_scoring_player(performances, starters_only=True, bench_only=False, position_filter="TE")
        if res:
            label, _ = res
            winner_text = label
    elif key == "highest_scoring_k_starter":
        res = _winner_highest_scoring_player(performances, starters_only=True, bench_only=False, position_filter="K")
        if res:
            label, _ = res
            winner_text = label
    elif key == "highest_scoring_flex_starter":
        res = _winner_highest_scoring_player(performances, starters_only=True, bench_only=False, positions_filter=["RB","WR","TE"])
        if res:
            label, _ = res
            winner_text = label
    elif key == "highest_team_bench_points":
        by_team: Dict[str, float] = {}
        for p in performances:
            if not p.get("fantasy_team"):
                continue
            if not p.get("is_bench"):
                continue
            try:
                pts = float(p.get("points", 0.0))
            except Exception:
                pts = 0.0
            by_team[p["fantasy_team"]] = by_team.get(p["fantasy_team"], 0.0) + pts
        if by_team:
            team, total = max(by_team.items(), key=lambda kv: kv[1])
            winner_text = f"{team} – {round(total,1)} bench pts"
    elif key == "most_20_plus_point_starters":
        by_team: Dict[str, int] = {}
        for p in performances:
            if not p.get("fantasy_team") or p.get("is_bench"):
                continue
            try:
                pts = float(p.get("points", 0.0))
            except Exception:
                pts = 0.0
            if pts >= 20.0:
                by_team[p["fantasy_team"]] = by_team.get(p["fantasy_team"], 0) + 1
        if by_team:
            team, count = max(by_team.items(), key=lambda kv: kv[1])
            winner_text = f"{team} – {count} starters with 20+"
    elif key == "most_15_plus_point_starters":
        by_team: Dict[str, int] = {}
        for p in performances:
            if not p.get("fantasy_team") or p.get("is_bench"):
                continue
            try:
                pts = float(p.get("points", 0.0))
            except Exception:
                pts = 0.0
            if pts >= 15.0:
                by_team[p["fantasy_team"]] = by_team.get(p["fantasy_team"], 0) + 1
        if by_team:
            team, count = max(by_team.items(), key=lambda kv: kv[1])
            winner_text = f"{team} – {count} starters with 15+"
    elif key == "most_10_plus_point_bench_players":
        by_team: Dict[str, int] = {}
        for p in performances:
            if not p.get("fantasy_team") or not p.get("is_bench"):
                continue
            try:
                pts = float(p.get("points", 0.0))
            except Exception:
                pts = 0.0
            if pts >= 10.0:
                by_team[p["fantasy_team"]] = by_team.get(p["fantasy_team"], 0) + 1
        if by_team:
            team, count = max(by_team.items(), key=lambda kv: kv[1])
            winner_text = f"{team} – {count} bench players with 10+"
    elif key.startswith("custom_incentive_week_"):
        winner_text = ""

    return {"title": title, "winner_text": winner_text}


