"""Shared chat + scheduling logic (extracted from Streamlit chatbot.py)."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from zoneinfo import ZoneInfo

import yaml
from openai import OpenAI

from app.calendar import (
    add_sessions_to_calendar,
    calendar_timezone,
    list_upcoming_events,
)

PROMPTS_PATH = Path(__file__).parent / "config.yaml"


def load_prompts() -> Dict[str, Any]:
    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calendar_busy_intervals(max_results: int = 50) -> List[Dict[str, str]]:
    try:
        upcoming = list_upcoming_events(max_results=max_results)
    except Exception:
        return []
    out: List[Dict[str, str]] = []
    for e in upcoming or []:
        start_info = e.get("start")
        end_info = e.get("end")
        if start_info and end_info:
            out.append({"start": start_info, "end": end_info})
    return out


def busy_context_string(intervals: List[Dict[str, str]]) -> str:
    if not intervals:
        return "[]"
    parts = [f"{{'start': '{it['start']}', 'end': '{it['end']}'}}" for it in intervals]
    return "[" + ", ".join(parts) + "]"


def build_plain_text_system(
    prompts: Dict[str, Any],
    today_str: str,
    rest_day: str,
    duration_min: int,
    busy_context: str,
) -> str:
    return prompts["plain_text_system_prompt"].format(
        today_str=today_str,
        rest_day=rest_day,
        duration_min=duration_min,
        busy_context=busy_context,
    )


def openai_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def stream_chat_completion(
    *,
    client: OpenAI,
    model: str,
    system_prompt: str,
    conversation: List[Dict[str, str]],
) -> Iterator[str]:
    """Yields text deltas from the assistant (OpenAI streaming)."""
    api_messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for msg in conversation:
        role = msg["role"]
        if role == "system":
            continue
        if role in ("agent", "assistant"):
            api_role = "assistant"
        elif role == "user":
            api_role = "user"
        else:
            continue
        api_messages.append({"role": api_role, "content": msg["content"]})

    stream = client.chat.completions.create(
        model=model,
        messages=api_messages,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


def _parse_iso_dt(value: str, local_tz: ZoneInfo) -> datetime:
    if len(value) == 10:
        return datetime.fromisoformat(value + "T00:00:00").replace(tzinfo=local_tz)
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=local_tz)
    return dt.astimezone(local_tz)


def _to_session_interval(sess: dict, local_tz: ZoneInfo) -> Tuple[datetime, datetime]:
    start_str = f"{sess['date']}T{sess['time']}:00"
    start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=local_tz)
    end_dt = start_dt + timedelta(minutes=int(sess["duration_min"]))
    return start_dt, end_dt


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def schedule_from_last_assistant(
    *,
    client: OpenAI,
    model: str,
    last_assistant_plain: str,
    busy_context: str,
) -> Dict[str, Any]:
    """
    Convert last assistant plan to JSON sessions, filter conflicts, write to Calendar.
    Returns a dict with keys: ok, scheduled_count, errors, warnings, conflicting_sessions.
    """
    prompts = load_prompts()
    today_str = date.today().isoformat()
    convert_system = prompts["convert_system_prompt"].format(
        today_str=today_str,
        busy_context=busy_context,
    )
    convert_messages = [
        {"role": "system", "content": convert_system},
        {"role": "user", "content": last_assistant_plain},
    ]

    try:
        conv = client.chat.completions.create(
            model=model,
            messages=convert_messages,
            stream=False,
        )
        raw = conv.choices[0].message.content or ""
        raw = raw.replace("```", "").strip()
        sessions = json.loads(raw)
    except Exception as err:
        return {
            "ok": False,
            "scheduled_count": 0,
            "errors": [f"Failed to convert to JSON sessions: {err}"],
            "warnings": [],
            "conflicting_sessions": [],
        }

    required_keys = {"date", "time", "duration_min", "title", "description"}
    valid_sessions: List[dict] = []
    warnings: List[str] = []
    if not isinstance(sessions, list):
        sessions = []

    for i, s in enumerate(sessions):
        if not isinstance(s, dict):
            continue
        missing = required_keys - set(s.keys())
        if missing:
            warnings.append(f"Session #{i + 1} missing fields: {missing}; skipping")
            continue
        valid_sessions.append(s)

    if not valid_sessions:
        return {
            "ok": False,
            "scheduled_count": 0,
            "errors": ["No valid sessions found to schedule."],
            "warnings": warnings,
            "conflicting_sessions": [],
        }

    try:
        busy = list_upcoming_events(max_results=250)
    except Exception:
        busy = []

    local_tz = ZoneInfo(calendar_timezone())
    busy_intervals: List[Tuple[datetime, datetime]] = []
    for e in busy:
        s = e.get("start")
        t = e.get("end")
        if not s or not t:
            continue
        try:
            busy_intervals.append((_parse_iso_dt(s, local_tz), _parse_iso_dt(t, local_tz)))
        except Exception:
            continue

    non_conflicting: List[dict] = []
    conflicting: List[dict] = []
    for sess in valid_sessions:
        s_dt, e_dt = _to_session_interval(sess, local_tz)
        has_conflict = any(_overlaps(s_dt, e_dt, b0, b1) for (b0, b1) in busy_intervals)
        if has_conflict:
            conflicting.append(sess)
        else:
            non_conflicting.append(sess)

    if conflicting:
        warnings.append(f"Skipping {len(conflicting)} session(s) due to conflicts.")

    if not non_conflicting:
        return {
            "ok": False,
            "scheduled_count": 0,
            "errors": ["No sessions to add after conflict filtering."],
            "warnings": warnings,
            "conflicting_sessions": conflicting,
        }

    try:
        add_sessions_to_calendar(non_conflicting)
    except Exception as err:
        return {
            "ok": False,
            "scheduled_count": 0,
            "errors": [f"Failed to write to calendar: {err}"],
            "warnings": warnings,
            "conflicting_sessions": conflicting,
        }

    return {
        "ok": True,
        "scheduled_count": len(non_conflicting),
        "errors": [],
        "warnings": warnings,
        "conflicting_sessions": conflicting,
    }
