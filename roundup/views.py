from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseNotFound
from django.urls import reverse
from django.utils.crypto import salted_hmac
import logging

logger = logging.getLogger(__name__)

from .espn_utils import get_league, get_league_cached, get_playoff_team_count
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
from django.core.cache import cache
from .services.performance_cache import (
    get_cached_scoreboard,
    cache_scoreboard,
    get_cached_standings,
    cache_standings,
    get_cached_player_performances,
    cache_player_performances,
    get_cached_weekly_awards,
    cache_weekly_awards,
)
from .services.draft_service import get_draft_analysis
from .ai_client import (
    generate_weekly_narrative,
    generate_overview,
    generate_storylines,
    generate_matchup_highlights,
)
from .ai_jobs import ensure_job, get_job_result
import os
import httpx
from urllib.parse import urlencode


def homepage(request):
    # Get current year and week for navigation
    from datetime import datetime
    current_date = datetime.now()
    current_year = current_date.year

    # For now, default to week 1 of current year
    default_week = 1

    # Use current league standings to enumerate players/teams
    league = get_league_cached(year=current_year)
    standings = get_standings_with_movement(league, default_week)
    
    # Preload all team logos for better performance
    from .services.logo_service import bulk_preload_logos_for_context
    teams = getattr(league, "teams", []) or []
    team_logos = bulk_preload_logos_for_context(teams)

    context = {
        'current_year': current_year,
        'default_week': default_week,
        'standings': standings,
        'team_logos': team_logos,  # Pass logos to template
        # Prizes
        'grand_prize': 250,
        'weekly_prize': 8,
    }
    return render(request, "roundup/homepage.html", context)


def team_logo(request: HttpRequest, team_id: int) -> HttpResponse:
    """Proxy a team's custom logo through our server using ESPN auth cookies.

    Some ESPN-hosted custom logos return 401 when fetched directly from the client
    because they require the SWID/espn_s2 cookies. We fetch them server-side and
    stream the bytes with appropriate content-type and caching.
    """
    from django.core.cache import cache
    from datetime import datetime
    
    # Check cache first
    cache_key = f"team_logo_{team_id}"
    cached_response = cache.get(cache_key)
    if cached_response:
        return cached_response
    
    # Resolve current year similar to homepage
    current_year = datetime.now().year
    try:
        league = get_league(year=current_year)
    except Exception:
        return HttpResponseNotFound()

    team = None
    for t in getattr(league, "teams", []) or []:
        if getattr(t, "team_id", None) == team_id:
            team = t
            break
    if team is None:
        return HttpResponseNotFound()

    logo_url = getattr(team, "logo_url", None)
    if not logo_url:
        return HttpResponseNotFound()

    swid = os.environ.get("ESPN_SWID")
    espn_s2 = os.environ.get("ESPN_S2")

    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            resp = client.get(logo_url, headers={"User-Agent": "Mozilla/5.0"}, cookies={"SWID": swid or "", "espn_s2": espn_s2 or ""})
            if resp.status_code != 200 or not resp.content:
                return HttpResponseNotFound()
            content_type = resp.headers.get("content-type", "image/png")
            response = HttpResponse(resp.content, content_type=content_type)
            response["Cache-Control"] = "public, max-age=86400"
            
            # Cache the response for 24 hours (86400 seconds)
            cache.set(cache_key, response, 86400)
            return response
    except Exception:
        return HttpResponseNotFound()

def weekly_report(request: HttpRequest, year: int, week: int) -> HttpResponse:
    """Render the weekly report page with minimal data and no ESPN calls for instant loading."""
    # Avoid fetching league to eliminate blocking calls; use safe defaults
    league_name = "League"
    playoff_team_count = 6
    prev_week = max(1, week - 1)
    next_week = min(18, week + 1)
    prev_disabled = (prev_week == week)
    next_disabled = (next_week == week)

    # Static assets only; defer logos and data to AJAX endpoints
    from .services.logo_service import preload_nfl_team_logos
    nfl_logos = preload_nfl_team_logos()

    context = {
        "league_name": league_name,
        "year": year,
        "week": week,
        "playoff_team_count": playoff_team_count,
        "prev_week": prev_week,
        "next_week": next_week,
        "prev_disabled": prev_disabled,
        "next_disabled": next_disabled,
        "team_logos": {},
        "nfl_logos": nfl_logos,
        # Empty placeholders for components that will load via AJAX
        "scoreboard": [],
        "standings": [],
        "incentives": {},
        "position_leaders": {},
        "positions": ["QB", "RB", "WR", "TE", "K", "DEF"],
        "weekly_incentive": {
            "this_title": "",
            "winner_text": "",
            "next_title": "",
        },
        "narrative": {},
        "awards": [],
    }

    return render(request, "roundup/report.html", context)


def weekly_report_narrative_api(request: HttpRequest, year: int, week: int) -> JsonResponse:
    """Return the AI-generated narrative as JSON. Intended to be called by the client after initial page render."""
    league = get_league_cached(year=year)
    league_name = getattr(getattr(league, "settings", None), "name", str(league.league_id))

    scoreboard = get_scoreboard(league, week)
    standings = get_standings_with_movement(league, week)
    incentives = compute_incentives(scoreboard)

    prompt_inputs = build_prompt_inputs(league_name, week, scoreboard, standings, incentives)
    narrative = generate_weekly_narrative(prompt_inputs)
    return JsonResponse(narrative)


def weekly_report_overview_api(request: HttpRequest, year: int, week: int) -> JsonResponse:
    league = get_league_cached(year=year)
    league_name = getattr(getattr(league, "settings", None), "name", str(league.league_id))
    
    # Preload NFL logos for player data
    from .services.logo_service import preload_nfl_team_logos
    nfl_logos = preload_nfl_team_logos()
    
    scoreboard = get_scoreboard(league, week)
    standings = get_standings_with_movement(league, week)
    incentives = compute_incentives(scoreboard)
    top_players = get_top_players(league, week, top_n=3, nfl_logos=nfl_logos)
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
    league = get_league_cached(year=year)
    league_name = getattr(getattr(league, "settings", None), "name", str(league.league_id))
    
    # Preload NFL logos for player data
    from .services.logo_service import preload_nfl_team_logos
    nfl_logos = preload_nfl_team_logos()
    
    scoreboard = get_scoreboard(league, week)
    standings = get_standings_with_movement(league, week)
    incentives = compute_incentives(scoreboard)
    top_players = get_top_players(league, week, top_n=3, nfl_logos=nfl_logos)
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
    
    # Preload NFL logos for player data
    from .services.logo_service import preload_nfl_team_logos
    nfl_logos = preload_nfl_team_logos()
    
    scoreboard = get_scoreboard(league, week)
    standings = get_standings_with_movement(league, week)
    incentives = compute_incentives(scoreboard)
    top_players = get_top_players(league, week, top_n=3, nfl_logos=nfl_logos)
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


# Component API endpoints for progressive loading
def weekly_report_scoreboard_api(request: HttpRequest, year: int, week: int) -> JsonResponse:
    """Return scoreboard data for progressive loading."""
    try:
        league = get_league_cached(year=year)
        
        # Preload team logos
        from .services.logo_service import bulk_preload_logos_for_context
        teams = getattr(league, "teams", []) or []
        team_logos = bulk_preload_logos_for_context(teams)
        
        # Get scoreboard data (cache at view layer)
        scoreboard = get_cached_scoreboard(league, week)
        if scoreboard is None:
            scoreboard = get_scoreboard(league, week)
            cache_scoreboard(league, week, scoreboard)
        
        # Standings (cache at view layer)
        standings = get_cached_standings(league, week)
        if standings is None:
            standings = get_standings_with_movement(league, week)
            cache_standings(league, week, standings)
        
        # Build mapping from team_id to record to enrich scoreboard display
        id_to_record = _build_team_id_to_record(standings)
        for m in scoreboard:
            hid = m.get("home_id")
            aid = m.get("away_id")
            m["home_record"] = id_to_record.get(hid) if hid is not None else None
            m["away_record"] = id_to_record.get(aid) if aid is not None else None
        
        return JsonResponse({
            "scoreboard": scoreboard,
            "team_logos": team_logos
        })
    except Exception as e:
        logger.error(f"Error loading scoreboard: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def weekly_report_standings_api(request: HttpRequest, year: int, week: int) -> JsonResponse:
    """Return standings data for progressive loading."""
    try:
        league = get_league_cached(year=year)
        standings = get_cached_standings(league, week)
        if standings is None:
            standings = get_standings_with_movement(league, week)
            cache_standings(league, week, standings)
        return JsonResponse({"standings": standings})
    except Exception as e:
        logger.error(f"Error loading standings: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def weekly_report_booms_busts_api(request: HttpRequest, year: int, week: int) -> JsonResponse:
    """Return booms and busts data for progressive loading."""
    try:
        league = get_league_cached(year=year)
        
        # Preload NFL logos
        from .services.logo_service import preload_nfl_team_logos
        nfl_logos = preload_nfl_team_logos()
        
        # Get player performances and compute booms/busts
        logger.info(f"Loading player performances for week {week}")
        all_performances = get_cached_player_performances(league, week)
        if all_performances is None:
            all_performances = get_all_player_performances(league, week, nfl_logos)
            cache_player_performances(league, week, all_performances)
        logger.info(f"Got {len(all_performances)} player performances")
        
        # Get top and bottom players
        logger.info("Getting top and bottom players")
        top_players = get_top_players(league, week, top_n=3, nfl_logos=nfl_logos)
        bottom_players = get_bottom_players(league, week, bottom_n=3, nfl_logos=nfl_logos)
        logger.info(f"Got {len(top_players)} top players and {len(bottom_players)} bottom players")
        
        # Compute boom/bust by position
        logger.info("Computing boom/bust by position")
        # Compute using D/ST to capture all defense codes, then normalize label to DEF for the frontend
        positions = ["QB", "RB", "WR", "TE", "K", "D/ST"]
        boom_bust = compute_boom_bust_by_position(all_performances, positions=positions)
        for row in boom_bust:
            pos = str(row.get("position") or "").upper()
            if pos in {"D/ST", "DST", "DEF"}:
                row["position"] = "DEF"
        logger.info(f"Computed boom/bust for {len(boom_bust)} positions")
        
        # Create a minimal incentives structure without calling compute_incentives
        incentives = {
            "top_players": top_players,
            "bottom_players": bottom_players,
            "boom_bust_by_position": boom_bust
        }
        
        return JsonResponse({
            "incentives": incentives,
            "nfl_logos": nfl_logos
        })
    except Exception as e:
        logger.error(f"Error loading booms and busts: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({"error": str(e)}, status=500)


def weekly_report_awards_api(request: HttpRequest, year: int, week: int) -> JsonResponse:
    """Return weekly awards data for progressive loading."""
    try:
        league = get_league_cached(year=year)
        
        # Get required data (use caches where available)
        scoreboard = get_cached_scoreboard(league, week)
        if scoreboard is None:
            scoreboard = get_scoreboard(league, week)
            cache_scoreboard(league, week, scoreboard)
        standings = get_cached_standings(league, week)
        if standings is None:
            standings = get_standings_with_movement(league, week)
            cache_standings(league, week, standings)
        all_performances = get_cached_player_performances(league, week)
        if all_performances is None:
            all_performances = get_all_player_performances(league, week)
            cache_player_performances(league, week, all_performances)
        
        # Compute awards
        awards = get_cached_weekly_awards(league, week)
        if awards is None:
            awards = compute_weekly_awards(scoreboard, standings, all_performances)
            cache_weekly_awards(league, week, awards)
        
        return JsonResponse({"awards": awards})
    except Exception as e:
        logger.error(f"Error loading awards: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def weekly_report_incentive_api(request: HttpRequest, year: int, week: int) -> JsonResponse:
    """Return the dynamic weekly incentive details (title, current leader text, next week's title)."""
    try:
        league = get_league(year=year)

        # Determine schedule and which incentive applies this week and next
        first_week = getattr(league, "firstScoringPeriod", 1) or 1
        last_week = getattr(league, "finalScoringPeriod", 18) or 18
        total_weeks = max(1, (last_week - first_week + 1))
        schedule = generate_weekly_incentive_schedule(total_weeks)
        idx = max(0, min(len(schedule) - 1, week - first_week))

        this_key = schedule[idx]
        next_key = schedule[idx + 1] if (idx + 1) < len(schedule) else None
        this_title = describe_incentive_title(this_key)
        next_title = describe_incentive_title(next_key) if next_key else ""

        # Compute current leader/winner text based on live data
        scoreboard = get_scoreboard(league, week)
        incentives_summary = compute_incentives(scoreboard)
        performances = get_all_player_performances(league, week)
        winner_info = compute_incentive_winner(
            this_key,
            scoreboard=scoreboard,
            incentives_summary=incentives_summary,
            performances=performances,
        )

        weekly_incentive = {
            "this_title": this_title,
            "winner_text": (winner_info or {}).get("winner_text", ""),
            "next_title": next_title,
        }

        return JsonResponse({"weekly_incentive": weekly_incentive})
    except Exception as e:
        logger.error(f"Error loading weekly incentive: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def draft_analysis(request):
    """
    Display the draft analysis page with snake draft visualization.
    """
    try:
        league = get_league_cached()
        draft_data = get_draft_analysis(league)
        
        # Preload all team logos for better performance
        from .services.logo_service import bulk_preload_logos_for_context, preload_nfl_team_logos
        teams = getattr(league, "teams", []) or []
        team_logos = bulk_preload_logos_for_context(teams)
        nfl_logos = preload_nfl_team_logos()
        
        context = {
            'league_name': getattr(getattr(league, "settings", None), "name", str(league.league_id)),
            'league_year': getattr(league, "year", "Unknown"),
            'draft_data': draft_data,
            'team_logos': team_logos,  # Add cached logos to context
            'nfl_logos': nfl_logos,  # Add cached NFL logos to context
        }
        
        return render(request, 'roundup/draft_analysis_simple.html', context)
    except Exception as e:
        logger.error(f"Error loading draft analysis: {e}")
        context = {
            'error': f"Unable to load draft data: {str(e)}",
            'draft_data': {
                "draft_picks": [],
                "team_drafts": [],
                "rounds": 0,
                "total_picks": 0,
                "teams_count": 0
            }
        }
        return render(request, 'roundup/draft_analysis_simple.html', context)


# === PDF EXPORT ===
def weekly_report_export_pdf(request: HttpRequest, year: int, week: int) -> HttpResponse:
    """Render the weekly report in print mode and export as a PDF using Playwright.
    Loads the same report URL with ?print=1 so CSS can adapt, waits for content,
    then prints to PDF and streams it back as a download.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return HttpResponse(f"Playwright not available: {e}", status=500)

    # Build absolute URL to the report page with print mode
    base_url = request.build_absolute_uri(reverse('weekly_report', kwargs={"year": year, "week": week}))
    url = f"{base_url}?print=1"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        # Load and wait for network idle so progressive components finish
        page.goto(url, wait_until="networkidle")
        # Ensure print media rules apply (use report-print.css only)
        try:
            page.emulate_media(media="print")
        except Exception:
            pass
        # Wait until client sets readiness flag to ensure all components rendered
        try:
            page.wait_for_function("() => window.__REPORT_COMPONENTS_READY__ === true", timeout=5000)
        except Exception:
            # Fallback small wait
            page.wait_for_timeout(500)
        # Use a slight scale-down and tighter margins to fit into two pages
        pdf_bytes = page.pdf(
            format="Letter",
            margin={"top": "0.2in", "right": "0.2in", "bottom": "0.2in", "left": "0.2in"},
            print_background=True,
            scale=1.0,
        )
        context.close()
        browser.close()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="weekly-report-{year}-week-{week}.pdf"'
    return response
