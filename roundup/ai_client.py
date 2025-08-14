import os
import json
from typing import Dict, Any
import httpx

try:
    from openai import OpenAI
except ImportError:  # Optional dependency
    OpenAI = None  # type: ignore


def _get_client_and_model():
    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if provider == "ollama":
        if OpenAI is None:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        api_key = os.environ.get("OLLAMA_API_KEY", "ollama")  # dummy key
        # Allow configurable timeout to avoid client-side 5m cancellations while Ollama is still generating
        timeout_env = os.environ.get("OLLAMA_TIMEOUT_SECONDS")
        try:
            timeout_seconds = float(timeout_env) if timeout_env else 900.0  # default 15 minutes
        except ValueError:
            timeout_seconds = 900.0
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.Client(timeout=timeout_seconds),
        )
        model = os.environ.get("LLM_MODEL", "llama3")  # Use faster model by default
        return client, model
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


def _sanitize_overview(text: str) -> str:
    """Remove boilerplate prefaces like "Here's a short overview..." or "Overview:" and return concise text."""
    import re

    if not text:
        return text

    cleaned = text.strip().strip('"').strip()

    # Remove leading 'Overview:' or 'Summary:' labels (case-insensitive)
    cleaned = re.sub(
        r"^(overview|summary)\s*:\s*",
        "",
        cleaned,
        count=1,
        flags=re.IGNORECASE
    )

    # Remove common prefaces like "Here's/Here is a (short|quick) (overview|summary) ...:"
    cleaned = re.sub(
        r"^(here(?:'|’)s|here is)\s+(?:a\s+)?(?:short\s+|quick\s+)?(?:overview|summary)(?:\s+of[^:]*?)?:\s*",
        "",
        cleaned,
        count=1,
        flags=re.IGNORECASE
    )

    return cleaned.strip()



def generate_weekly_narrative(prompt_inputs: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate short, consistent narrative sections as JSON using an LLM.

    Returns a dict with keys: overview, storylines, matchup_highlights, standings_blurb, incentives_blurb.
    """
    try:
        client, model = _get_client_and_model()
    except Exception as e:
        # Fallback: deterministic text if no LLM configured
        print(f"ERROR{e}")
        return {
            "overview": "Weekly roundup unavailable (LLM not configured).",
            "storylines": "",
            "matchup_highlights": "",
            "standings_blurb": "",
            "incentives_blurb": "",
        }

    system_prompt = (
        "Generate NFL fantasy weekly roundup as JSON with a single key: overview. "
        "Tone: informative, light-hearted, conversational. "
        "Notice close games (margins < 5), first wins after a drought, and undefeated teams. "
        "You may mention one standout NFL player if provided. "
        "Start directly with the content; do not include prefaces like 'Here's...' or labels like 'Overview:'. "
        "Output JSON only. Keep overview under 100 words."
    )

    user_prompt = (
        "Create weekly roundup:\n" +
        json.dumps(prompt_inputs, ensure_ascii=False)
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,  # Lower temperature for more consistent output
            max_tokens=300,   # Reduced token limit for faster generation
            stream=False,
            top_p=0.8,        # Slightly lower for faster generation
        )
    except Exception as e:
        # Fallback: deterministic text if no LLM configured
        print(f"ERROR{e}")
        return {
            "overview": f"Weekly roundup unavailable {e}.",
            "storylines": "",
            "matchup_highlights": "",
            "standings_blurb": "",
            "incentives_blurb": "",
        }

    content = response.choices[0].message.content  # type: ignore[attr-defined]
    try:
        data = json.loads(content)
        # Ensure required keys exist and are strings
        for key in [
            "overview",
            # We now only require overview but keep normalization tolerant
            "storylines",
            "matchup_highlights",
            "standings_blurb",
            "incentives_blurb",
        ]:
            if key not in data:
                data[key] = ""
            elif not isinstance(data[key], str):
                # Convert non-string values to string representation
                if isinstance(data[key], list):
                    # Handle arrays by converting to a readable string
                    if key == "matchup_highlights" and data[key]:
                        # Convert matchup highlights array to readable text
                        highlights = []
                        for highlight in data[key]:
                            if isinstance(highlight, dict):
                                home = highlight.get("home", "Unknown")
                                away = highlight.get("away", "Unknown")
                                winner = highlight.get("winner", "Unknown")
                                highlights.append(f"{home} vs {away} - {winner} won")
                            else:
                                highlights.append(str(highlight))
                        data[key] = "; ".join(highlights)
                    else:
                        data[key] = "; ".join(str(item) for item in data[key])
                else:
                    data[key] = str(data[key])
        # Sanitize overview phrasing
        if data.get("overview"):
            data["overview"] = _sanitize_overview(data["overview"])
        return data
    except Exception:
        return {
            "overview": _sanitize_overview(content[:500]) if content else "",
            "storylines": "",
            "matchup_highlights": "",
            "standings_blurb": "",
            "incentives_blurb": "",
        }


def _chat_once(system_prompt: str, user_payload: Dict[str, Any], *, max_tokens: int = 160) -> str:
    """Small helper to send a single, targeted request and return raw text content."""
    try:
        client, model = _get_client_and_model()
    except Exception:
        return ""

    user_prompt = json.dumps(user_payload, ensure_ascii=False)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=max_tokens,
            stream=False,
            top_p=0.8,
        )
        return response.choices[0].message.content or ""
    except Exception:
        return ""


def generate_overview(prompt_inputs: Dict[str, Any]) -> str:
    """Generate a concise weekly overview string only."""
    payload = {
        "league_name": prompt_inputs.get("league_name"),
        "week": prompt_inputs.get("week"),
        # Minimal context for speed
        "scoreboard": prompt_inputs.get("scoreboard", [])[:3],
        "standings_top5": prompt_inputs.get("standings_top5", [])[:3],
        "top_players": prompt_inputs.get("top_players", [])[:3],
        "close_games": prompt_inputs.get("close_games", [])[:2],
        "undefeated_teams": prompt_inputs.get("undefeated_teams", [])[:2],
        "first_wins": prompt_inputs.get("first_wins", [])[:2],
    }
    system = (
        "Return ONLY a short overview (max 50-60 words). Tone: informative, light-hearted. "
        "Highlight close games, wins if they havn't won in the last 3, or undefeated teams if present. Optionally mention one standout player. "
        "Start directly with the content; no prefaces like 'Here's...' and no labels like 'Overview:'."
    )
    text = _chat_once(system, payload, max_tokens=80)
    # Ensure plain text
    try:
        # Some models might return JSON; normalize to string
        obj = json.loads(text)
        if isinstance(obj, dict) and "overview" in obj:
            return _sanitize_overview(str(obj.get("overview", "")))
    except Exception:
        pass
    return _sanitize_overview(text.strip())


def generate_storylines(prompt_inputs: Dict[str, Any]) -> str:
    """Generate concise storylines paragraph only."""
    payload = {
        "league_name": prompt_inputs.get("league_name"),
        "week": prompt_inputs.get("week"),
        "scoreboard": prompt_inputs.get("scoreboard", []),
        "standings_top5": prompt_inputs.get("standings_top5", [])[:5],
        "top_players": prompt_inputs.get("top_players", [])[:3],
    }
    system = (
        "Return ONLY a concise paragraph (max 60 words) of key storylines. Plain text only. Tone: light-hearted. "
        "Call out upsets, streaks, big jumps in standings, and one standout NFL player if applicable."
    )
    text = _chat_once(system, payload, max_tokens=120)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "storylines" in obj:
            return str(obj.get("storylines", ""))
    except Exception:
        pass
    return text.strip()


def generate_matchup_highlights(prompt_inputs: Dict[str, Any]) -> str:
    """Generate concise matchup highlights paragraph only."""
    payload = {
        "league_name": prompt_inputs.get("league_name"),
        "week": prompt_inputs.get("week"),
        "scoreboard": prompt_inputs.get("scoreboard", []),
        "top_players": prompt_inputs.get("top_players", [])[:3],
    }
    system = (
        "Return ONLY a concise paragraph (max 60 words) summarizing notable matchups and outcomes. Plain text only. "
        "Use a friendly, casual tone. If there was a very close game (margin < 5), react to it (e.g., 'Wow!')."
    )
    text = _chat_once(system, payload, max_tokens=120)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "matchup_highlights" in obj:
            return str(obj.get("matchup_highlights", ""))
    except Exception:
        pass
    return text.strip()
