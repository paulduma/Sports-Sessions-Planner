#!/usr/bin/env python3
"""
Sports Calendar Manager MVP
A single-file tool to parse training programs and schedule them in Google Calendar
"""

import os
import json
import pickle
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import pytz

import click
from dotenv import load_dotenv
import openai
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar']
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
TIMEZONE = os.getenv('TIMEZONE', 'UTC')
DEFAULT_DURATION = int(os.getenv('DEFAULT_SESSION_DURATION', '60'))
PREFERRED_START = os.getenv('PREFERRED_START_TIME', '09:00')
PREFERRED_END = os.getenv('PREFERRED_END_TIME', '18:00')

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

@dataclass
class Session:
    """Represents a single training session"""
    title: str
    type: str
    duration_minutes: int
    intensity: str
    notes: str
    suggested_date: Optional[str] = None

@dataclass
class TrainingProgram:
    """Represents a complete training program"""
    name: str
    sessions: List[Session]
    total_weeks: int

class SportsPlanner:
    """Main application class"""
    
    def __init__(self):
        self.calendar_service = None
        self.timezone = pytz.timezone(TIMEZONE)
    
    def authenticate_google(self) -> None:
        """Authenticate with Google Calendar API"""
        creds = None
        
        # Load existing token
        if os.path.exists('token.json'):
            creds = pickle.load(open('token.json', 'rb'))
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    click.echo("❌ credentials.json not found!")
                    click.echo("Please follow Google Calendar API setup instructions.")
                    return
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open('token.json', 'wb') as token:
                pickle.dump(creds, token)
        
        self.calendar_service = build('calendar', 'v3', credentials=creds)
        click.echo("✅ Google Calendar authenticated successfully!")
    
    def parse_program_with_ai(self, program_text: str) -> TrainingProgram:
        """Use OpenAI to parse training program text"""
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        prompt = f"""
        Parse this training program text into structured sessions. Extract:
        - Session title/name
        - Type of exercise (cardio, strength, flexibility, etc.)
        - Duration in minutes
        - Intensity level (low, medium, high)
        - Any additional notes
        
        Return as JSON with this structure:
        {{
            "program_name": "extracted program name",
            "total_weeks": estimated_weeks,
            "sessions": [
                {{
                    "title": "session name",
                    "type": "exercise type", 
                    "duration_minutes": duration_number,
                    "intensity": "low/medium/high",
                    "notes": "any additional info"
                }}
            ]
        }}
        
        Training program text:
        {program_text}
        """
        
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a fitness program parser. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            parsed_data = json.loads(response.choices[0].message.content)
            
            sessions = [
                Session(
                    title=s['title'],
                    type=s['type'],
                    duration_minutes=s['duration_minutes'],
                    intensity=s['intensity'],
                    notes=s['notes']
                ) for s in parsed_data['sessions']
            ]
            
            return TrainingProgram(
                name=parsed_data['program_name'],
                sessions=sessions,
                total_weeks=parsed_data['total_weeks']
            )
            
        except Exception as e:
            click.echo(f"❌ Error parsing program: {e}")
            raise
    
    def suggest_schedule_with_ai(self, program: TrainingProgram, start_date: str) -> List[Session]:
        """Use AI to suggest optimal scheduling"""
        sessions_info = [
            f"{s.title} ({s.type}, {s.duration_minutes}min, {s.intensity} intensity)"
            for s in program.sessions
        ]
        
        prompt = f"""
        Create an optimal weekly schedule for these training sessions starting from {start_date}.
        Consider:
        - Preferred time window: {PREFERRED_START} to {PREFERRED_END}
        - Allow rest days between high intensity sessions
        - Distribute sessions evenly throughout the week
        - Total program duration: {program.total_weeks} weeks
        
        Sessions to schedule:
        {chr(10).join(sessions_info)}
        
        Return suggested dates in YYYY-MM-DD format for each session, in order.
        Return as JSON array: ["2024-01-15", "2024-01-17", ...]
        """
        
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a fitness scheduling expert. Always return valid JSON array of dates."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            suggested_dates = json.loads(response.choices[0].message.content)
            
            # Update sessions with suggested dates
            scheduled_sessions = []
            for i, session in enumerate(program.sessions):
                if i < len(suggested_dates):
                    session.suggested_date = suggested_dates[i]
                scheduled_sessions.append(session)
            
            return scheduled_sessions
            
        except Exception as e:
            click.echo(f"⚠️  Error with AI scheduling, using simple distribution: {e}")
            return self._simple_schedule(program.sessions, start_date)
    
    def _simple_schedule(self, sessions: List[Session], start_date: str) -> List[Session]:
        """Fallback simple scheduling if AI fails"""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        scheduled = []
        
        for i, session in enumerate(sessions):
            # Schedule every other day
            session_date = start + timedelta(days=i * 2)
            session.suggested_date = session_date.strftime('%Y-%m-%d')
            scheduled.append(session)
        
        return scheduled
    
    def create_calendar_events(self, sessions: List[Session]) -> None:
        """Create Google Calendar events for scheduled sessions"""
        if not self.calendar_service:
            click.echo("❌ Google Calendar not authenticated")
            return
        
        created_count = 0
        
        for session in sessions:
            if not session.suggested_date:
                continue
                
            try:
                # Parse date and create datetime
                session_date = datetime.strptime(session.suggested_date, '%Y-%m-%d')
                start_time = datetime.strptime(PREFERRED_START, '%H:%M').time()
                
                start_datetime = datetime.combine(session_date, start_time)
                start_datetime = self.timezone.localize(start_datetime)
                end_datetime = start_datetime + timedelta(minutes=session.duration_minutes)
                
                event = {
                    'summary': f"🏃 {session.title}",
                    'description': f"Type: {session.type}\\nIntensity: {session.intensity}\\nNotes: {session.notes}",
                    'start': {
                        'dateTime': start_datetime.isoformat(),
                        'timeZone': TIMEZONE,
                    },
                    'end': {
                        'dateTime': end_datetime.isoformat(),
                        'timeZone': TIMEZONE,
                    },
                }
                
                self.calendar_service.events().insert(
                    calendarId=GOOGLE_CALENDAR_ID, 
                    body=event
                ).execute()
                
                created_count += 1
                click.echo(f"✅ Created: {session.title} on {session.suggested_date}")
                
            except Exception as e:
                click.echo(f"❌ Failed to create event for {session.title}: {e}")
        
        click.echo(f"\\n🎉 Successfully created {created_count} calendar events!")

# CLI Interface
@click.group()
def cli():
    """Sports Calendar Manager - Schedule your training programs with AI"""
    pass

@cli.command()
@click.argument('program_file', type=click.File('r'))
@click.option('--start-date', default=None, help='Start date (YYYY-MM-DD), defaults to tomorrow')
def schedule(program_file, start_date):
    """Parse a training program and schedule it in Google Calendar"""
    
    # Set default start date to tomorrow
    if not start_date:
        start_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    click.echo(f"📅 Scheduling program starting from {start_date}")
    
    # Read program text
    program_text = program_file.read()
    click.echo(f"📖 Read program text ({len(program_text)} characters)")
    
    planner = SportsPlanner()
    
    try:
        # Parse program with AI
        click.echo("🤖 Parsing program with AI...")
        program = planner.parse_program_with_ai(program_text)
        click.echo(f"✅ Parsed '{program.name}' with {len(program.sessions)} sessions")
        
        # Generate schedule with AI
        click.echo("📋 Generating optimal schedule...")
        scheduled_sessions = planner.suggest_schedule_with_ai(program, start_date)
        
        # Show preview
        click.echo("\\n📅 Scheduled Sessions:")
        for session in scheduled_sessions:
            click.echo(f"  • {session.suggested_date}: {session.title} ({session.duration_minutes}min)")
        
        # Confirm before creating events
        if click.confirm("\\nCreate these events in Google Calendar?"):
            planner.authenticate_google()
            planner.create_calendar_events(scheduled_sessions)
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")

@cli.command()
def setup():
    """Setup Google Calendar authentication"""
    click.echo("🔧 Setting up Google Calendar authentication...")
    planner = SportsPlanner()
    planner.authenticate_google()

@cli.command()
@click.argument('text')
@click.option('--start-date', default=None)
def quick(text, start_date):
    """Quick schedule from command line text"""
    if not start_date:
        start_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    planner = SportsPlanner()
    
    try:
        click.echo("🤖 Parsing text with AI...")
        program = planner.parse_program_with_ai(text)
        
        click.echo("📋 Generating schedule...")
        scheduled_sessions = planner.suggest_schedule_with_ai(program, start_date)
        
        click.echo("\\n📅 Scheduled Sessions:")
        for session in scheduled_sessions:
            click.echo(f"  • {session.suggested_date}: {session.title}")
        
        if click.confirm("\\nCreate in Google Calendar?"):
            planner.authenticate_google()
            planner.create_calendar_events(scheduled_sessions)
            
    except Exception as e:
        click.echo(f"❌ Error: {e}")

if __name__ == '__main__':
    cli()
