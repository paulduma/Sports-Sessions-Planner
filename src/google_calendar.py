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


def list_upcoming_events(max_results: int = 5, calendar_id: str = "primary") -> List[Dict[str, Any]]:
    service = get_calendar_service()
    now_utc = dt.datetime.utcnow().isoformat() + "Z"

    res = service.events().list(
        calendarId=calendar_id,
        timeMin=now_utc,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = res.get("items", [])
    out: List[Dict[str, Any]] = []

    for e in events:
        start = e.get("start", {})
        end = e.get("end", {})
        start_dt = start.get("dateTime") or start.get("date")
        end_dt = end.get("dateTime") or end.get("date")

        out.append({
            "summary": e.get("summary", "(no title)"),
            "start": start_dt,
            "end": end_dt,
            "id": e.get("id"),
            "htmlLink": e.get("htmlLink"),
        })

    return out


def add_sessions_to_calendar(sessions: List[Dict], calendar_id: str = "primary"):
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

        created = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"Created: {created['summary']} on {created['start']['dateTime']}")
