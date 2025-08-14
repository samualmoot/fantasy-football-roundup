from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.crypto import salted_hmac

from .espn_utils import get_league, get_playoff_team_count
from .services.espn_service import (
    get_scoreboard,
    get_standings_with_movement,
    get_top_players,
    get_previous_standings,
    get_bottom_players,
    get_all_player_performances,
    compute_position_leaders,
)
from .services.espn_service import _build_team_id_to_record  # internal helper for view formatting
from .incentives import (
    generate_weekly_incentive_schedule,
    compute_incentive_winner,
    describe_incentive_title,
    compute_boom_bust_by_position,
    compute_weekly_awards,
)
from .services.report_builder import compute_incentives, build_prompt_inputs
from .ai_client import (
    generate_weekly_narrative,
    generate_overview,
    generate_storylines,
    generate_matchup_highlights,
)
from .ai_jobs import ensure_job, get_job_result


def homepage(request):
    return redirect('weekly_report', year=2025, week=1)

def weekly_report(request: HttpRequest, year: int, week: int) -> HttpResponse:
    league = get_league(year=year)
    league_name = getattr(getattr(league, "settings", None), "name", str(league.league_id))
    playoff_team_count = get_playoff_team_count(league)

    # Boundaries for navigation
    first_week = getattr(league, "firstScoringPeriod", 1) or 1
    last_week = getattr(league, "finalScoringPeriod", 18) or 18
    prev_week = max(first_week, week - 1)
    next_week = min(last_week, week + 1)
    prev_disabled = week <= first_week
    next_disabled = week >= last_week

    scoreboard = get_scoreboard(league, week)
    standings = get_standings_with_movement(league, week)
    # Build mapping from team_id to record to enrich scoreboard display
    id_to_record = _build_team_id_to_record(standings)
    for m in scoreboard:
        hid = m.get("home_id")
        aid = m.get("away_id")
        m["home_record"] = id_to_record.get(hid) if hid is not None else None
        m["away_record"] = id_to_record.get(aid) if aid is not None else None
    incentives = compute_incentives(scoreboard)
    incentives["top_players"] = get_top_players(league, week, top_n=3)
    incentives["bottom_players"] = get_bottom_players(league, week, bottom_n=3)
    # Build boom/bust by position (starters only)
    all_performances = get_all_player_performances(league, week)
    incentives["boom_bust_by_position"] = compute_boom_bust_by_position(all_performances)

    # Determine regular season length and compute weekly incentive schedule
    # ESPN settings commonly expose finalScoringPeriod as last week index
    first_week = getattr(league, "firstScoringPeriod", 1) or 1
    last_week = getattr(league, "finalScoringPeriod", 18) or 18
    regular_season_weeks = max(1, last_week - first_week + 1)
    schedule = generate_weekly_incentive_schedule(regular_season_weeks)
    # Calculate index relative to first week
    idx = min(max(0, week - first_week), len(schedule) - 1)
    this_incentive_key = schedule[idx]
    next_incentive_key = schedule[idx + 1] if idx + 1 < len(schedule) else schedule[0]

    # Compute the winner depending on the incentive type
    performances = all_performances
    incentive_result = compute_incentive_winner(
        this_incentive_key,
        scoreboard=scoreboard,
        incentives_summary=incentives,
        performances=performances,
    )
    # Position leaders/busts
    position_leaders = compute_position_leaders(performances, top_n=1, bottom_n=1)

    # Do NOT block on AI here; page should render immediately.
    # The narrative will be fetched asynchronously via a JSON endpoint.
    narrative = {}
    context = {
        "league_name": league_name,
        "year": year,
        "week": week,
        "playoff_team_count": playoff_team_count,
        "prev_week": prev_week,
        "next_week": next_week,
        "prev_disabled": prev_disabled,
        "next_disabled": next_disabled,
        "scoreboard": scoreboard,
        "standings": standings,
        "incentives": incentives,
        "position_leaders": position_leaders,
        "positions": ["QB", "RB", "WR", "TE", "K", "DEF"],
        "weekly_incentive": {
            "this_title": describe_incentive_title(this_incentive_key),
            "winner_text": incentive_result.get("winner_text", ""),
            "next_title": describe_incentive_title(next_incentive_key),
        },
        "narrative": narrative,
    }
    # Weekly awards
    context["awards"] = compute_weekly_awards(scoreboard, standings, all_performances)
    return render(request, "roundup/report.html", context)


def weekly_report_narrative_api(request: HttpRequest, year: int, week: int) -> JsonResponse:
    """Return the AI-generated narrative as JSON. Intended to be called by the client after initial page render."""
    league = get_league(year=year)
    league_name = getattr(getattr(league, "settings", None), "name", str(league.league_id))

    scoreboard = get_scoreboard(league, week)
    standings = get_standings_with_movement(league, week)
    incentives = compute_incentives(scoreboard)

    prompt_inputs = build_prompt_inputs(league_name, week, scoreboard, standings, incentives)
    narrative = generate_weekly_narrative(prompt_inputs)
    return JsonResponse(narrative)


def weekly_report_overview_api(request: HttpRequest, year: int, week: int) -> JsonResponse:
    league = get_league(year=year)
    league_name = getattr(getattr(league, "settings", None), "name", str(league.league_id))
    scoreboard = get_scoreboard(league, week)
    standings = get_standings_with_movement(league, week)
    incentives = compute_incentives(scoreboard)
    top_players = get_top_players(league, week, top_n=3)
    previous = get_previous_standings(league, week)
    inputs = build_prompt_inputs(league_name, week, scoreboard, standings, incentives, top_players, previous)
    cache_key = salted_hmac("overview", f"{league_name}:{year}:{week}").hexdigest()

    def job():
        return {"overview": generate_overview(inputs)}

    state = ensure_job(cache_key, job)
    if state == "pending":
        return JsonResponse({"status": "pending"}, status=202)
    result = get_job_result(cache_key)
    return JsonResponse(result or {"overview": ""})


def weekly_report_storylines_api(request: HttpRequest, year: int, week: int) -> JsonResponse:
    league = get_league(year=year)
    league_name = getattr(getattr(league, "settings", None), "name", str(league.league_id))
    scoreboard = get_scoreboard(league, week)
    standings = get_standings_with_movement(league, week)
    incentives = compute_incentives(scoreboard)
    top_players = get_top_players(league, week, top_n=3)
    previous = get_previous_standings(league, week)
    inputs = build_prompt_inputs(league_name, week, scoreboard, standings, incentives, top_players, previous)
    cache_key = salted_hmac("storylines", f"{league_name}:{year}:{week}").hexdigest()

    def job():
        return {"storylines": generate_storylines(inputs)}

    state = ensure_job(cache_key, job)
    if state == "pending":
        return JsonResponse({"status": "pending"}, status=202)
    result = get_job_result(cache_key)
    return JsonResponse(result or {"storylines": ""})


def weekly_report_highlights_api(request: HttpRequest, year: int, week: int) -> JsonResponse:
    league = get_league(year=year)
    league_name = getattr(getattr(league, "settings", None), "name", str(league.league_id))
    scoreboard = get_scoreboard(league, week)
    standings = get_standings_with_movement(league, week)
    incentives = compute_incentives(scoreboard)
    top_players = get_top_players(league, week, top_n=3)
    previous = get_previous_standings(league, week)
    inputs = build_prompt_inputs(league_name, week, scoreboard, standings, incentives, top_players, previous)
    cache_key = salted_hmac("highlights", f"{league_name}:{year}:{week}").hexdigest()

    def job():
        return {"matchup_highlights": generate_matchup_highlights(inputs)}

    state = ensure_job(cache_key, job)
    if state == "pending":
        return JsonResponse({"status": "pending"}, status=202)
    result = get_job_result(cache_key)
    return JsonResponse(result or {"matchup_highlights": ""})
