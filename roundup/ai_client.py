import os
import json
from typing import Dict, Any

try:
    from openai import OpenAI
except ImportError:  # Optional dependency
    OpenAI = None  # type: ignore


def _get_client_and_model():
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()
    if provider == "groq":
        if OpenAI is None:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY environment variable.")
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        model = os.environ.get("LLM_MODEL", "llama-3.1-8b-instant")
        return client, model
    elif provider == "openai":
        if OpenAI is None:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY environment variable.")
        client = OpenAI(api_key=api_key)
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        return client, model
    elif provider == "ollama":
        if OpenAI is None:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        api_key = os.environ.get("OLLAMA_API_KEY", "ollama")  # dummy key
        client = OpenAI(api_key=api_key, base_url=base_url)
        model = os.environ.get("LLM_MODEL", "llama3.1")
        return client, model
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


def generate_weekly_narrative(prompt_inputs: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate short, consistent narrative sections as JSON using an LLM.

    Returns a dict with keys: overview, storylines, matchup_highlights, standings_blurb, incentives_blurb.
    """
    try:
        client, model = _get_client_and_model()
    except Exception as e:
        # Fallback: deterministic text if no LLM configured
        return {
            "overview": "Weekly roundup unavailable (LLM not configured).",
            "storylines": "",
            "matchup_highlights": "",
            "standings_blurb": "",
            "incentives_blurb": "",
        }

    system_prompt = (
        "You are generating an NFL fantasy weekly roundup. Keep tone informative and concise. "
        "Output strictly JSON with keys: overview, storylines, matchup_highlights, standings_blurb, incentives_blurb. "
        "Do not include markdown; no prose outside JSON. Keep each value under 80 words."
    )

    user_prompt = (
        "Create a weekly roundup based on this data. Maintain consistent structure.\n" +
        json.dumps(prompt_inputs, ensure_ascii=False)
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=600,
    )

    content = response.choices[0].message.content  # type: ignore[attr-defined]
    try:
        data = json.loads(content)
        # Ensure required keys exist
        for key in [
            "overview",
            "storylines",
            "matchup_highlights",
            "standings_blurb",
            "incentives_blurb",
        ]:
            data.setdefault(key, "")
        return data
    except Exception:
        return {
            "overview": content[:500] if content else "",
            "storylines": "",
            "matchup_highlights": "",
            "standings_blurb": "",
            "incentives_blurb": "",
        }
