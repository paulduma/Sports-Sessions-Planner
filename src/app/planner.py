# AI planning logic

import json
import yaml
from pathlib import Path
from openai import OpenAI

client = OpenAI()

# Load YAML prompt
PROMPTS_PATH = Path(__file__).parent / "config.yaml"
with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
    PROMPTS = yaml.safe_load(f)

def render_system_prompt(preferred_time: str, rest_day: str, duration_min: int) -> str:
    """Fill placeholders in the YAML prompt."""
    return PROMPTS["base_system_prompt"].format(
        preferred_time=preferred_time,
        rest_day=rest_day,
        duration_min=duration_min,
    )

def generate_plan(user_text: str, prefs: dict) -> list[dict]:
    """Call OpenAI and return a structured list of sessions."""
    system_prompt = render_system_prompt(
        preferred_time=prefs.get("preferred_time", "Morning"),
        rest_day=prefs.get("rest_day", "Sunday"),
        duration_min=prefs.get("duration_min", 60),
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    )

    raw_output = response.choices[0].message.content.strip()

    # Defensive JSON parsing
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        # Try to strip code fences if GPT wrapped output in ```json
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1].replace("json", "", 1)
            return json.loads(raw_output.strip())
        raise ValueError(f"AI did not return valid JSON: {raw_output}")
