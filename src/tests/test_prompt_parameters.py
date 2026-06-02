#!/usr/bin/env python3
"""Verify sidebar parameters are inserted into the planning system prompt."""

import sys
from datetime import date
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from planner import (
    build_plain_text_system,
    busy_context_string,
    load_prompts,
    upcoming_events_context_string,
)


def test_prompt_formatting():
    prompts = load_prompts()
    busy_context = busy_context_string([])
    upcoming_events = upcoming_events_context_string(
        [
            {
                "summary": "Course footing",
                "start": "2026-06-03T18:00:00+02:00",
                "end": "2026-06-03T19:00:00+02:00",
            }
        ]
    )
    today_str = date.today().isoformat()

    test_cases = [
        {"rest_day": "Aucun", "duration_min": 60, "description": "Default values"},
        {"rest_day": "Dimanche", "duration_min": 45, "description": "Sunday rest, 45min sessions"},
        {"rest_day": "Vendredi", "duration_min": 90, "description": "Friday rest, 90min sessions"},
        {
            "rest_day": "Samedi, Dimanche",
            "duration_min": 60,
            "description": "Weekend rest days",
        },
    ]

    for test_case in test_cases:
        system_prompt = build_plain_text_system(
            prompts,
            today_str=today_str,
            rest_day=test_case["rest_day"],
            duration_min=test_case["duration_min"],
            busy_context=busy_context,
            upcoming_events=upcoming_events,
        )
        assert test_case["rest_day"] in system_prompt
        assert str(test_case["duration_min"]) in system_prompt
        assert today_str in system_prompt
        assert "Course footing" in system_prompt
        assert "Consulter l'agenda" in system_prompt
        assert "Valider et planifier" in system_prompt


def test_upcoming_events_empty():
    text = upcoming_events_context_string([])
    assert "aucun événement" in text.lower()


if __name__ == "__main__":
    test_prompt_formatting()
    print("All prompt parameter tests passed.")
