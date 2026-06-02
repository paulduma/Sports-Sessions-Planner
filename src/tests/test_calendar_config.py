#!/usr/bin/env python3
"""Verify multi-calendar env parsing and event merge ordering."""

import os
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from google_calendar import (
    _event_start_sort_key,
    _parse_calendar_ids,
    read_calendar_ids,
    write_calendar_id,
)


def test_parse_calendar_ids_defaults():
    assert _parse_calendar_ids(None) == ["primary"]
    assert _parse_calendar_ids("") == ["primary"]
    assert _parse_calendar_ids("   ") == ["primary"]


def test_parse_calendar_ids_multiple():
    assert _parse_calendar_ids("primary, work@example.com") == [
        "primary",
        "work@example.com",
    ]


def test_read_and_write_calendar_env(monkeypatch=None):
    old_read = os.environ.pop("GOOGLE_CALENDAR_IDS", None)
    old_write = os.environ.pop("GOOGLE_WRITE_CALENDAR_ID", None)
    try:
        os.environ["GOOGLE_CALENDAR_IDS"] = "primary, work@example.com"
        os.environ["GOOGLE_WRITE_CALENDAR_ID"] = "work@example.com"
        assert read_calendar_ids() == ["primary", "work@example.com"]
        assert write_calendar_id() == "work@example.com"
    finally:
        if old_read is None:
            os.environ.pop("GOOGLE_CALENDAR_IDS", None)
        else:
            os.environ["GOOGLE_CALENDAR_IDS"] = old_read
        if old_write is None:
            os.environ.pop("GOOGLE_WRITE_CALENDAR_ID", None)
        else:
            os.environ["GOOGLE_WRITE_CALENDAR_ID"] = old_write


def test_event_start_sort_key():
    assert _event_start_sort_key({"start": {"dateTime": "2026-06-03T10:00:00+02:00"}}) == (
        "2026-06-03T10:00:00+02:00"
    )
    assert _event_start_sort_key({"start": {"date": "2026-06-03"}}) == "2026-06-03"
    assert _event_start_sort_key({"start": "2026-06-03T10:00:00+02:00"}) == (
        "2026-06-03T10:00:00+02:00"
    )


if __name__ == "__main__":
    test_parse_calendar_ids_defaults()
    test_parse_calendar_ids_multiple()
    test_read_and_write_calendar_env()
    test_event_start_sort_key()
    print("All calendar config tests passed.")
