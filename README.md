# Sports Calendar Manager

## 🎯 Goal

Build, test, and explore different approaches using AI agents to schedule my sports sessions


## Project Overview

This will be a small desktop tool that converts **plain-text sports training programs** into structured sessions and schedules them directly into my **Google Calendar**, using preferences I have set
It uses **a single AI model (via OpenAI API)** for parsing and planning, and Python logic for event creation

## MVP Core features 

1. **Text Input of Training Programs**
    - Users provide training sessions as plain text (via CLI).
2. **Program Parsing & Planning**
    - One AI-powered component extracts workouts (type, duration, intensity, notes).
    - Outputs a planned list of sessions with suggested scheduling.
3. **Calendar Integration**
    - Python logic writes the planned sessions into Google Calendar.
    - Handles time zones and avoids obvious conflicts.
4. **CLI Interface**
    - Simple commands to add programs and view scheduled events.


## Long term ambition / ideas

- **Refined Interfaces**: GUI (Gradio/Streamlit)
- **New Input Types**: PDF, images, URLs, voice input
- **Smarter Scheduling**: AI-driven adjustments, rescheduling missed sessions.
- **Multi-Agent Setup**: For better specialization (parser, scheduler, calendar manager).
- **Integrations**: Export to Garmin, Strava, etc.