"""
Google Calendar Integration Module

This module provides functionality to authenticate with Google Calendar API
and retrieve calendar events. It handles OAuth2 authentication flow and
manages credentials securely.

Key Features:
- OAuth2 authentication with Google Calendar API
- Automatic token refresh when expired
- Retrieval of upcoming calendar events
- Secure credential management

Dependencies:
- google-auth-oauthlib: For OAuth2 flow
- google-auth: For credential management
- google-api-python-client: For Calendar API interaction
"""

from __future__ import annotations
import datetime as dt
from pathlib import Path
from typing import List, Dict, Any

# Google API authentication and service libraries
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Configuration constants
SCOPES = ["https://www.googleapis.com/auth/calendar"]  # Read access to Google Calendar
CREDENTIALS_PATH = Path(__file__).parents[2] / "credentials" / "credentials.json"  # OAuth2 client secrets
TOKEN_PATH = Path(__file__).parents[2] / "credentials" / "token.json"  # Stored user credentials
DEFAULT_TZ = "Europe/Paris"  # Default timezone for calendar operations

def get_calendar_service():
    """
    Authenticate with Google Calendar API and return service object.
    
    This function implements the OAuth2 authentication flow:
    1. Checks if stored credentials exist and are valid
    2. Refreshes expired credentials if refresh token is available
    3. Initiates new OAuth flow if no valid credentials exist
    4. Saves credentials for future use
    
    Returns:
        googleapiclient.discovery.Resource: Authenticated Calendar API service
        
    Raises:
        FileNotFoundError: If credentials.json is missing
        google.auth.exceptions.RefreshError: If token refresh fails
    """
    creds = None
    
    # Try to load existing credentials from token file
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    
    # Check if credentials are valid or need refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired credentials using refresh token
            creds.refresh(Request())
        else:
            # No valid credentials - start new OAuth flow
            # This will open a browser window for user authentication
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for future use
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    
    # Build and return the Calendar API service
    return build("calendar", "v3", credentials=creds)

def list_upcoming_events(max_results: int = 5, calendar_id: str = "primary") -> List[Dict[str, Any]]:
    """
    Retrieve upcoming events from Google Calendar.
    
    This function fetches a list of upcoming events from the specified calendar,
    starting from the current time. It's primarily used for testing the calendar
    connection and getting a quick overview of scheduled events.
    
    Args:
        max_results (int): Maximum number of events to retrieve (default: 5)
        calendar_id (str): Calendar ID to query (default: "primary" for user's main calendar)
        
    Returns:
        List[Dict[str, Any]]: List of event dictionaries containing:
            - summary: Event title/name
            - start: Event start time (ISO format)
            - id: Unique event identifier
            - htmlLink: Direct link to event in Google Calendar
            
    Raises:
        googleapiclient.errors.HttpError: If API request fails
        google.auth.exceptions.RefreshError: If authentication fails
    """
    # Get authenticated Calendar API service
    service = get_calendar_service()
    
    # Get current time in RFC3339 UTC format (required by Google Calendar API)
    now_utc = dt.datetime.utcnow().isoformat() + "Z"
    
    # Query the Calendar API for upcoming events
    res = service.events().list(
        calendarId=calendar_id,        # Which calendar to query
        timeMin=now_utc,               # Only events starting from now
        maxResults=max_results,        # Limit number of results
        singleEvents=True,             # Expand recurring events into individual instances
        orderBy="startTime",           # Sort by start time (ascending)
    ).execute()
    
    # Extract events from API response
    events = res.get("items", [])
    out: List[Dict[str, Any]] = []
    
    # Process each event and extract relevant information
    for e in events:
        start = e.get("start", {})
        # Get start time - could be 'dateTime' (timed event) or 'date' (all-day event)
        start_dt = start.get("dateTime") or start.get("date")
        
        # Build simplified event dictionary
        out.append({
            "summary": e.get("summary", "(no title)"),  # Event title
            "start": start_dt,                          # Start time
            "id": e.get("id"),                         # Unique event ID
            "htmlLink": e.get("htmlLink"),             # Link to Google Calendar
        })
    
    return out
