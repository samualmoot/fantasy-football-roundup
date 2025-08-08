# ESPN Fantasy Football Team Object Attributes

| Attribute                | Data Type    | Description |
|--------------------------|--------------|-------------|
| team_id                  | int          | Unique identifier for the team in the league |
| team_abbrev              | str          | Team abbreviation (short code) |
| team_name                | str          | Full team name |
| division_id              | int          | ID of the division the team belongs to |
| division_name            | str          | Name of the division |
| wins                     | int          | Number of wins |
| losses                   | int          | Number of losses |
| ties                     | int          | Number of ties |
| points_for               | float        | Total points scored by the team |
| points_against           | float        | Total points scored against the team |
| acquisitions             | int          | Number of player acquisitions |
| acquisition_budget_spent | int          | Amount of acquisition budget spent |
| drops                    | int          | Number of players dropped |
| trades                   | int          | Number of trades made |
| move_to_ir               | int          | Number of moves to injured reserve |
| playoff_pct              | int/float    | Playoff percentage (may be 0 if not calculated) |
| draft_projected_rank     | int          | Projected rank after draft |
| streak_length            | int          | Length of current win/loss streak |
| streak_type              | str          | Type of streak ('WIN' or 'LOSS') |
| standing                 | int          | Current standing in the league |
| final_standing           | int          | Final standing (after season ends) |
| waiver_rank              | int          | Current waiver priority rank |
| logo_url                 | str (URL)    | URL to the team's logo image |
| roster                   | list[Player] | List of Player objects on the team |
| schedule                 | list[Team]   | List of Team objects representing the schedule |
| scores                   | list[float]  | List of weekly scores |
| outcomes                 | list[str]    | List of weekly outcomes ('W', 'L', 'T', 'U') |
| mov                      | list[float]  | List of margins of victory/defeat per week |
| owners                   | list[dict]   | List of owner info dicts (name, id, etc.) |
| stats                    | dict         | Dictionary of various team stats |

---

# ESPN Fantasy Football League Object Attributes

| Attribute              | Data Type         | Description |
|------------------------|-------------------|-------------|
| logger                 | Logger            | Logger object for espn-api internal logging |
| league_id              | int/str           | Unique identifier for the league |
| year                   | int               | Year/season of the league |
| teams                  | list[Team]        | List of Team objects in the league |
| members                | list[dict]        | List of league member info dicts |
| draft                  | list[Pick]        | List of Pick objects representing draft picks |
| player_map             | dict              | Mapping of player IDs to player info |
| espn_request           | object            | Internal espn-api request handler |
| currentMatchupPeriod   | int               | Current matchup period (week) |
| scoringPeriodId        | int               | Current scoring period ID |
| firstScoringPeriod     | int               | First scoring period of the season |
| finalScoringPeriod     | int               | Final scoring period of the season |
| previousSeasons        | list              | List of previous season data (if available) |
| current_week           | int               | Current NFL week (as seen by the league) |
| settings               | object            | League settings object (name, rules, etc.) |
| nfl_week               | int               | Current NFL week |

---

# ESPN Fantasy Football Member Dict Attributes

| Attribute             | Data Type      | Description |
|-----------------------|---------------|-------------|
| displayName           | str           | Member's display name (username or nickname) |
| firstName             | str           | Member's first name |
| id                    | str           | Unique identifier for the member |
| lastName              | str           | Member's last name |
| notificationSettings  | list[dict]    | List of notification settings for the member |

---

# ESPN Fantasy Football Draft Pick (Pick/BasePick) Object Attributes

| Attribute        | Data Type   | Description |
|------------------|------------|-------------|
| team             | Team       | Team object that made the pick |
| playerId         | int        | ESPN player ID of the drafted player |
| playerName       | str        | Name of the drafted player |
| round_num        | int        | Draft round number |
| round_pick       | int        | Pick number within the round |
| bid_amount       | int        | Bid amount (for auction drafts; 0 for snake drafts) |
| keeper_status    | bool       | Whether the pick was a keeper |
| nominatingTeam   | Team/None  | Team object that nominated the player (for auction drafts; None for snake drafts) |

Descriptions are based on espn-api and typical fantasy football league data. For more details, see the espn-api documentation or inspect the object in code.

---

## ESPN Configuration

Set credentials and league ID in `.env`:

```
ESPN_SWID={your_swid}
ESPN_S2={your_espn_s2}
# Optional: override default league
ESPN_LEAGUE_ID=123456789
```

The app defaults to the current year unless you pass a specific year in the URL.

---

## AI Integration (Groq, OpenAI, or Local Ollama)

This project generates a weekly roundup narrative via an OpenAI-compatible client. You can choose:
- Groq (often has a free tier)
- OpenAI (paid)
- Ollama (local, free)

Install dependency:

```bash
pip install openai
```

Choose a provider via `.env`:

```ini
# Provider: groq (default), openai, or ollama
LLM_PROVIDER=groq

# If using Groq:
GROQ_API_KEY=your_groq_api_key
# Optional model override
# LLM_MODEL=llama-3.1-8b-instant

# If using OpenAI (paid):
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_openai_api_key
# Optional model override
# LLM_MODEL=gpt-4o-mini

# If using local Ollama (free, runs on your machine):
# Install from https://ollama.com and pull a model, e.g.:
#   ollama pull llama3.1
# Then set:
# LLM_PROVIDER=ollama
# LLM_MODEL=llama3.1
# OLLAMA_BASE_URL=http://localhost:11434/v1  # default
```

Run the server and open the report page:

```bash
python manage.py runserver
# http://localhost:8000/report/<year>/<week>/
```

Notes:
- Ollama runs models locally; performance depends on your hardware. For faster responses, try smaller models.
- If no AI key/server is configured, the app renders a simple fallback narrative and still shows scores, incentives, and standings.
