from django.shortcuts import render
from django.http import HttpRequest, HttpResponse

from .espn_utils import get_league
from .services.espn_service import get_scoreboard, get_standings_with_movement
from .services.report_builder import compute_incentives, build_prompt_inputs
from .ai_client import generate_weekly_narrative


def weekly_report(request: HttpRequest, year: int, week: int) -> HttpResponse:
    league = get_league(year=year)
    league_name = getattr(getattr(league, "settings", None), "name", str(league.league_id))

    # Boundaries for navigation
    first_week = getattr(league, "firstScoringPeriod", 1) or 1
    last_week = getattr(league, "finalScoringPeriod", 18) or 18
    prev_week = max(first_week, week - 1)
    next_week = min(last_week, week + 1)
    prev_disabled = week <= first_week
    next_disabled = week >= last_week

    scoreboard = get_scoreboard(league, week)
    standings = get_standings_with_movement(league, week)
    incentives = compute_incentives(scoreboard)

    prompt_inputs = build_prompt_inputs(league_name, week, scoreboard, standings, incentives)
    narrative = generate_weekly_narrative(prompt_inputs)

    context = {
        "league_name": league_name,
        "year": year,
        "week": week,
        "prev_week": prev_week,
        "next_week": next_week,
        "prev_disabled": prev_disabled,
        "next_disabled": next_disabled,
        "scoreboard": scoreboard,
        "standings": standings,
        "incentives": incentives,
        "narrative": narrative,
    }
    return render(request, "roundup/report.html", context)
