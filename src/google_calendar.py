"""
Google Calendar integration: OAuth2, list upcoming events, create sessions.
"""

from __future__ import annotations

import datetime as dt
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
_REPO_ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = _REPO_ROOT / "credentials" / "credentials.json"
TOKEN_PATH = _REPO_ROOT / "credentials" / "token.json"


def _parse_calendar_ids(raw: str | None) -> List[str]:
    if not raw or not raw.strip():
        return ["primary"]
    ids = [part.strip() for part in raw.split(",") if part.strip()]
    return ids or ["primary"]


def read_calendar_ids() -> List[str]:
    """Calendar IDs to read for busy context and conflict checks."""
    return _parse_calendar_ids(os.environ.get("GOOGLE_CALENDAR_IDS"))


def write_calendar_id() -> str:
    """Calendar ID where training sessions are created."""
    raw = os.environ.get("GOOGLE_WRITE_CALENDAR_ID", "").strip()
    if raw:
        return raw
    return read_calendar_ids()[0]


def calendar_timezone() -> str:
    """IANA timezone for interpreting session date/time and Google Calendar writes."""
    return os.environ.get("TIMEZONE", "Europe/Paris")


def get_calendar_service():
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as refresh_error:
                print(f"Token refresh failed: {refresh_error}")
                creds = None

        if not creds or not creds.valid:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"OAuth credentials file not found at {CREDENTIALS_PATH}. "
                    "Please download your OAuth 2.0 credentials from Google Cloud Console "
                    "and save them as 'credentials.json' in the credentials folder."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return build("calendar", "v3", credentials=creds)


def list_accessible_calendars() -> List[Dict[str, str]]:
    """Return id + summary for calendars visible to the authenticated account."""
    service = get_calendar_service()
    res = service.calendarList().list().execute()
    out: List[Dict[str, str]] = []
    for entry in res.get("items", []):
        cal_id = entry.get("id")
        if not cal_id:
            continue
        out.append({
            "id": cal_id,
            "summary": entry.get("summary", cal_id),
            "primary": str(entry.get("primary", False)).lower(),
        })
    return out


def _event_start_sort_key(event: Dict[str, Any]) -> str:
    start = event.get("start")
    if isinstance(start, str):
        return start
    if isinstance(start, dict):
        return start.get("dateTime") or start.get("date") or ""
    return ""


def _normalize_event(event: Dict[str, Any], calendar_id: str) -> Dict[str, Any]:
    start = event.get("start", {})
    end = event.get("end", {})
    start_dt = start.get("dateTime") or start.get("date")
    end_dt = end.get("dateTime") or end.get("date")
    return {
        "summary": event.get("summary", "(no title)"),
        "start": start_dt,
        "end": end_dt,
        "id": event.get("id"),
        "htmlLink": event.get("htmlLink"),
        "calendarId": calendar_id,
    }


def _list_events_for_calendar(
    service: Any,
    calendar_id: str,
    *,
    time_min: str,
    max_results: int,
) -> List[Dict[str, Any]]:
    res = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return [
        _normalize_event(e, calendar_id)
        for e in res.get("items", [])
    ]


def list_upcoming_events(
    max_results: int = 5,
    calendar_ids: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """Fetch upcoming events from one or more calendars, merged by start time."""
    ids = calendar_ids if calendar_ids is not None else read_calendar_ids()
    if not ids:
        return []

    service = get_calendar_service()
    now_utc = dt.datetime.utcnow().isoformat() + "Z"
    merged: List[Dict[str, Any]] = []

    for cal_id in ids:
        try:
            merged.extend(
                _list_events_for_calendar(
                    service,
                    cal_id,
                    time_min=now_utc,
                    max_results=max_results,
                )
            )
        except Exception as err:
            print(f"Failed to list events for calendar {cal_id}: {err}")

    merged.sort(key=_event_start_sort_key)
    return merged[:max_results]


def calendar_connection_status(max_results: int = 1) -> Dict[str, Any]:
    """Connection probe plus read/write calendar configuration for the UI."""
    read_ids = read_calendar_ids()
    write_id = write_calendar_id()
    upcoming = list_upcoming_events(max_results=max_results, calendar_ids=read_ids)

    accessible = list_accessible_calendars()
    accessible_by_id = {c["id"]: c for c in accessible}
    read_set = set(read_ids)
    calendars: List[Dict[str, Any]] = []

    for cal_id in read_ids:
        meta = accessible_by_id.get(cal_id, {})
        calendars.append({
            "id": cal_id,
            "summary": meta.get("summary", cal_id),
            "read": True,
            "write": cal_id == write_id,
        })

    if write_id not in read_set:
        meta = accessible_by_id.get(write_id, {})
        calendars.append({
            "id": write_id,
            "summary": meta.get("summary", write_id),
            "read": False,
            "write": True,
        })

    return {
        "connected": True,
        "busy_sample_count": len(upcoming),
        "read_calendar_ids": read_ids,
        "write_calendar_id": write_id,
        "calendars": calendars,
    }


def add_sessions_to_calendar(
    sessions: List[Dict],
    calendar_id: str | None = None,
):
    target_calendar = calendar_id or write_calendar_id()
    service = get_calendar_service()
    tz_name = calendar_timezone()
    tz = ZoneInfo(tz_name)

    for sess in sessions:
        start_str = f"{sess['date']}T{sess['time']}:00"
        start_naive = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
        start_dt = start_naive.replace(tzinfo=tz)
        end_dt = start_dt + timedelta(minutes=int(sess["duration_min"]))

        event = {
            "summary": sess["title"],
            "description": sess["description"],
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": tz_name,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": tz_name,
            },
        }

        created = service.events().insert(calendarId=target_calendar, body=event).execute()
        print(f"Created: {created['summary']} on {created['start']['dateTime']}")
