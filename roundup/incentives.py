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


# NFL team logo helpers
_NFL_VALID_CODES = {
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB", "HOU", "IND",
    "JAX", "KC", "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO", "NYG", "NYJ", "PHI", "PIT", "SEA", "SF",
    "TB", "TEN", "WAS",
}
_NFL_NORMALIZE = {
    "JAC": "JAX",
    "WSH": "WAS",
    "LA": "LAR",
    "SD": "LAC",
    "STL": "LAR",
    "OAK": "LV",
}


def _nfl_logo_url(code: Any) -> str | None:
    if not code:
        return None
    abbr = str(code).upper()
    abbr = _NFL_NORMALIZE.get(abbr, abbr)
    if abbr not in _NFL_VALID_CODES:
        return None
    return f"https://static.www.nfl.com/league/api/clubs/logos/{abbr}.svg"


def _winner_from_scoreboard_highest(scoreboard: List[Dict[str, Any]]) -> Tuple[str, float, str | None] | None:
    best_name = None
    best_score = None
    best_owner = None
    for m in scoreboard:
        candidates = [
            (m.get("home_team"), m.get("home_score"), m.get("home_id"), m.get("home_owner")),
            (m.get("away_team"), m.get("away_score"), m.get("away_id"), m.get("away_owner")),
        ]
        for name, score, tid, owner in candidates:
            # Skip BYE and unknown teams (we set id=None for BYE in scoreboard)
            if tid is None:
                continue
            try:
                val = float(score)
            except Exception:
                val = None
            if name and val is not None and (best_score is None or val > best_score):
                best_name, best_score, best_owner = name, val, owner
    if best_name is None or best_score is None:
        return None
    return best_name, best_score, best_owner


def _winner_from_scoreboard_lowest(scoreboard: List[Dict[str, Any]]) -> Tuple[str, float, str | None] | None:
    worst_name = None
    worst_score = None
    worst_owner = None
    for m in scoreboard:
        candidates = [
            (m.get("home_team"), m.get("home_score"), m.get("home_id"), m.get("home_owner")),
            (m.get("away_team"), m.get("away_score"), m.get("away_id"), m.get("away_owner")),
        ]
        for name, score, tid, owner in candidates:
            # Skip BYE and unknown teams (we set id=None for BYE in scoreboard)
            if tid is None:
                continue
            try:
                val = float(score)
            except Exception:
                val = None
            if name and val is not None and (worst_score is None or val < worst_score):
                worst_name, worst_score, worst_owner = name, val, owner
    if worst_name is None or worst_score is None:
        return None
    return worst_name, worst_score, worst_owner


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
            name, pts, owner = res
            owner_text = f" ({owner})" if owner else ""
            winner_text = f"{name}{owner_text} ({pts})"
    elif key == "lowest_team_score":
        res = _winner_from_scoreboard_lowest(scoreboard)
        if res:
            name, pts, owner = res
            owner_text = f" ({owner})" if owner else ""
            winner_text = f"{name}{owner_text} ({pts})"
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


def compute_boom_bust_by_position(
    performances: List[Dict[str, Any]],
    *,
    positions: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """Return a list of rows with top 3 booms and busts per position (starters only).

    Each row: { position, booms: [top3_players], busts: [bottom3_players] }
    Each player: {player_name, points, fantasy_team, nfl_team, nfl_logo}
    Supports D/ST or DST equivalently.
    """
    if positions is None:
        positions = ["QB", "RB", "WR", "TE", "K", "D/ST"]

    # Normalize performances to starters and comparable position codes
    starters: List[Dict[str, Any]] = [p for p in performances if not p.get("is_bench")]

    def matches_position(p: Dict[str, Any], pos: str) -> bool:
        code = str(p.get("position") or "").upper()
        if pos.upper() == "D/ST":
            return code in {"D/ST", "DST", "DEF"}
        return code == pos.upper()

    def project(p: Dict[str, Any]) -> Dict[str, Any]:
        try:
            pts = round(float(p.get("points", 0.0) or 0.0), 1)
        except Exception:
            pts = 0.0
        nfl_team = p.get("nfl_team") or ""
        return {
            "player_name": p.get("player_name") or "Player",
            "points": pts,
            "fantasy_team": p.get("fantasy_team") or "",
            "nfl_team": nfl_team,
            "nfl_logo": p.get("nfl_logo") or _nfl_logo_url(nfl_team),  # Use cached logo if available, fallback to URL
        }

    rows: List[Dict[str, str]] = []
    for pos in positions:
        pool = [p for p in starters if matches_position(p, pos)]
        if not pool:
            rows.append({"position": pos, "booms": [], "busts": []})
            continue
        
        # Sort by points: highest first for booms, lowest first for busts
        sorted_pool = sorted(pool, key=lambda p: (p.get("points") or 0.0), reverse=True)
        
        # Top 3 booms (highest points)
        booms = [project(p) for p in sorted_pool[:3]]
        
        # Bottom 3 busts (lowest points)
        busts = [project(p) for p in sorted_pool[-3:]]
        
        rows.append({
            "position": pos,
            "booms": booms,
            "busts": busts,
        })
    return rows


def compute_weekly_awards(
    scoreboard: List[Dict[str, Any]],
    standings: List[Dict[str, Any]],
    performances: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Compute a set of fun weekly awards based on the week results.

    Returns a list of { title, text } entries suitable for display.
    """
    awards: List[Dict[str, str]] = []

    # Helper maps
    name_to_rank = {s.get("team_name"): s.get("rank") for s in standings}

    # Manager of the Week: highest team score
    best_name: str | None = None
    best_score: float | None = None
    best_owner: str | None = None
    for m in scoreboard:
        for name, score, owner in ((m.get("home_team"), m.get("home_score"), m.get("home_owner")), (m.get("away_team"), m.get("away_score"), m.get("away_owner"))):
            try:
                val = float(score)
            except Exception:
                val = None
            if name and val is not None and (best_score is None or val > best_score):
                best_name, best_score, best_owner = name, val, owner
    if best_name is not None and best_score is not None:
        owner_text = f" ({best_owner})" if best_owner else ""
        awards.append({
            "title": "Manager of the Week",
            "text": f"{best_name}{owner_text} – {round(best_score,1)} points",
        })

    # Squeaker: lowest winning score
    lowest_win_name: str | None = None
    lowest_win_points: float | None = None
    lowest_win_owner: str | None = None
    for m in scoreboard:
        winner = m.get("winner")
        if not winner:
            continue
        win_pts = m.get("home_score") if winner == m.get("home_team") else m.get("away_score")
        win_owner = m.get("home_owner") if winner == m.get("home_team") else m.get("away_owner")
        try:
            val = float(win_pts)
        except Exception:
            continue
        if lowest_win_points is None or val < lowest_win_points:
            lowest_win_points = val
            lowest_win_name = winner
            lowest_win_owner = win_owner
    if lowest_win_name is not None and lowest_win_points is not None:
        owner_text = f" ({lowest_win_owner})" if lowest_win_owner else ""
        awards.append({
            "title": "Squeaker",
            "text": f"Lowest winning score: {lowest_win_name}{owner_text} – {round(lowest_win_points,1)}",
        })

    # Heartbreaker: closest loss
    heartbreak_loser: str | None = None
    heartbreak_winner: str | None = None
    heartbreak_margin: float | None = None
    heartbreak_loser_owner: str | None = None
    heartbreak_winner_owner: str | None = None
    for m in scoreboard:
        winner = m.get("winner")
        if not winner:
            continue
        margin = m.get("margin")
        try:
            mg = float(margin)
        except Exception:
            continue
        # loser is the other team
        loser = m.get("home_team") if winner == m.get("away_team") else m.get("away_team")
        loser_owner = m.get("home_owner") if loser == m.get("home_team") else m.get("away_owner")
        winner_owner = m.get("home_owner") if winner == m.get("home_team") else m.get("away_owner")
        if heartbreak_margin is None or mg < heartbreak_margin:
            heartbreak_margin = mg
            heartbreak_loser = loser
            heartbreak_winner = winner
            heartbreak_loser_owner = loser_owner
            heartbreak_winner_owner = winner_owner
    if heartbreak_loser and heartbreak_winner and heartbreak_margin is not None:
        loser_owner_text = f" ({heartbreak_loser_owner})" if heartbreak_loser_owner else ""
        winner_owner_text = f" ({heartbreak_winner_owner})" if heartbreak_winner_owner else ""
        awards.append({
            "title": "Heartbreaker",
            "text": f"{heartbreak_loser}{loser_owner_text} lost to {heartbreak_winner}{winner_owner_text} by {round(heartbreak_margin,1)}",
        })

    # Giant Killer: upset where winner had worse rank than opponent; take biggest rank delta
    upset_winner: str | None = None
    upset_loser: str | None = None
    upset_delta: int | None = None
    upset_winner_owner: str | None = None
    upset_loser_owner: str | None = None
    for m in scoreboard:
        winner = m.get("winner")
        if not winner:
            continue
        home = m.get("home_team")
        away = m.get("away_team")
        loser = away if winner == home else home
        winner_owner = m.get("home_owner") if winner == home else m.get("away_owner")
        loser_owner = m.get("home_owner") if loser == home else m.get("away_owner")
        w_rank = name_to_rank.get(winner)
        l_rank = name_to_rank.get(loser)
        if isinstance(w_rank, int) and isinstance(l_rank, int) and w_rank > l_rank:
            delta = w_rank - l_rank
            if upset_delta is None or delta > upset_delta:
                upset_delta = delta
                upset_winner = winner
                upset_loser = loser
                upset_winner_owner = winner_owner
                upset_loser_owner = loser_owner
    if upset_winner and upset_loser and upset_delta is not None:
        winner_owner_text = f" ({upset_winner_owner})" if upset_winner_owner else ""
        loser_owner_text = f" ({upset_loser_owner})" if upset_loser_owner else ""
        awards.append({
            "title": "Giant Killer",
            "text": f"{upset_winner}{winner_owner_text} upset {upset_loser}{loser_owner_text} (by ranking, +{upset_delta})",
        })

    # Bench Blunder: most total bench points
    bench_points: Dict[str, float] = {}
    for p in performances:
        if not p.get("fantasy_team") or not p.get("is_bench"):
            continue
        try:
            pts = float(p.get("points", 0.0))
        except Exception:
            pts = 0.0
        bench_points[p["fantasy_team"]] = bench_points.get(p["fantasy_team"], 0.0) + pts
    if bench_points:
        team, total = max(bench_points.items(), key=lambda kv: kv[1])
        # Get owner name from standings
        team_owner = None
        for s in standings:
            if s.get("team_name") == team:
                team_owner = s.get("owner_name")
                break
        owner_text = f" ({team_owner})" if team_owner else ""
        awards.append({
            "title": "Bench Blunder",
            "text": f"{team}{owner_text} – {round(total,1)} points left on bench",
        })

    return awards


