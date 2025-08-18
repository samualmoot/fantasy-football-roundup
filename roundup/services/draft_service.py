from typing import List, Dict, Any, Optional
from espn_api.football import League
from ..espn_utils import get_league

def get_draft_data(league: Optional[League] = None) -> Dict[str, Any]:
    """
    Extract and process draft data from ESPN API.
    Returns structured data for the draft analysis page.
    """
    if league is None:
        league = get_league()
    
    if not hasattr(league, 'draft') or not league.draft:
        return {
            "draft_picks": [],
            "teams": [],
            "rounds": 0,
            "total_picks": 0
        }
    
    # Build a mapping of player IDs to NFL teams and positions from team rosters
    player_info_map = {}
    for team in league.teams:
        if hasattr(team, 'roster') and team.roster:
            for player in team.roster:
                if hasattr(player, 'playerId'):
                    player_id = getattr(player, 'playerId')
                    nfl_team = getattr(player, 'proTeam', None)
                    position = getattr(player, 'position', None)
                    if player_id:
                        player_info_map[player_id] = {
                            'nfl_team': nfl_team,
                            'position': position
                        }
    
    # Process draft picks
    draft_picks = []
    for pick in league.draft:
        try:
            player_id = getattr(pick, 'playerId', None)
            player_info = player_info_map.get(player_id, {}) if player_id else {}
            
            # Extract pick information
            pick_data = {
                "round": getattr(pick, 'round_num', 0),
                "pick_number": getattr(pick, 'round_pick', 0),
                "overall_pick": len(draft_picks) + 1,
                "player_name": getattr(pick, 'playerName', 'Unknown Player'),
                "player_id": player_id,
                "nfl_team": player_info.get('nfl_team'),  # Add NFL team information
                "position": player_info.get('position'),   # Add position information
                "team_name": getattr(pick.team, 'team_name', 'Unknown Team') if hasattr(pick, 'team') else 'Unknown Team',
                "team_id": getattr(pick.team, 'team_id', None) if hasattr(pick, 'team') else None,
                "team_abbrev": getattr(pick.team, 'team_abbrev', '') if hasattr(pick, 'team') else '',
                "team_logo": getattr(pick.team, 'logo_url', None) if hasattr(pick, 'team') else None,
                "owner_name": getattr(pick.team, 'owners', [{}])[0].get('firstName', '') + ' ' + getattr(pick.team, 'owners', [{}])[0].get('lastName', '') if hasattr(pick.team, 'owners') and pick.team.owners else None,
            }
            draft_picks.append(pick_data)
        except Exception as e:
            print(f"Error processing pick: {e}")
            continue
    
    # Calculate draft statistics
    total_picks = len(draft_picks)
    rounds = max(pick["round"] for pick in draft_picks) if draft_picks else 0
    
    # Group picks by team for analysis
    team_drafts = {}
    for pick in draft_picks:
        team_id = pick["team_id"]
        if team_id not in team_drafts:
            team_drafts[team_id] = {
                "team_id": team_id,
                "team_name": pick["team_name"],
                "team_abbrev": pick["team_abbrev"],
                "team_logo": pick["team_logo"],
                "picks": [],
                "total_picks": 0,
                "rounds_covered": set(),
                "positions_drafted": set()
            }
        
        team_drafts[team_id]["picks"].append(pick)
        team_drafts[team_id]["total_picks"] += 1
        team_drafts[team_id]["rounds_covered"].add(pick["round"])
    
    # Convert sets to lists for JSON serialization
    for team in team_drafts.values():
        team["rounds_covered"] = sorted(list(team["rounds_covered"]))
        team["positions_drafted"] = list(team["positions_drafted"])
    
    return {
        "draft_picks": draft_picks,
        "team_drafts": list(team_drafts.values()),
        "rounds": rounds,
        "total_picks": total_picks,
        "teams_count": len(team_drafts)
    }

def get_draft_analysis(league: Optional[League] = None) -> Dict[str, Any]:
    """
    Get comprehensive draft analysis including grades and insights.
    """
    draft_data = get_draft_data(league)
    
    if not draft_data["draft_picks"]:
        return draft_data
    
    # Add draft analysis
    analysis = analyze_draft_strategy(draft_data)
    draft_data["analysis"] = analysis
    
    return draft_data

def analyze_draft_strategy(draft_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze draft strategies and provide insights.
    """
    team_drafts = draft_data["team_drafts"]
    
    # Calculate draft grades based on ADP vs actual draft position
    # This is a simplified grading system - you can enhance it later
    for team in team_drafts:
        picks = team["picks"]
        
        # Simple grading based on pick distribution
        early_rounds = len([p for p in picks if p["round"] <= 3])
        mid_rounds = len([p for p in picks if 4 <= p["round"] <= 8])
        late_rounds = len([p for p in picks if p["round"] >= 9])
        
        # Basic strategy identification
        if early_rounds >= 2:
            strategy = "Early Round Focus"
        elif mid_rounds >= 3:
            strategy = "Balanced Approach"
        elif late_rounds >= 4:
            strategy = "Late Round Value"
        else:
            strategy = "Mixed Strategy"
        
        team["draft_strategy"] = strategy
        
        # Simple grade (A, B, C, D) - you can enhance this later
        if early_rounds >= 2 and mid_rounds >= 2:
            grade = "A"
        elif early_rounds >= 1 and mid_rounds >= 2:
            grade = "B"
        elif mid_rounds >= 2:
            grade = "C"
        else:
            grade = "D"
        
        team["draft_grade"] = grade
    
    return {
        "total_teams": len(team_drafts),
        "grade_distribution": {
            "A": len([t for t in team_drafts if t["draft_grade"] == "A"]),
            "B": len([t for t in team_drafts if t["draft_grade"] == "B"]),
            "C": len([t for t in team_drafts if t["draft_grade"] == "C"]),
            "D": len([t for t in team_drafts if t["draft_grade"] == "D"])
        }
    }
