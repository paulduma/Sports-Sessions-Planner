# Sports Calendar Manager

## Goal

A personal sports coach chatbot that reads your Google Calendar, proposes training sessions in free slots, and writes confirmed sessions back to Calendar.

## How it works

1. **Chat** — Describe your training goals; the assistant proposes a plain-text plan using your calendar busy times, rest day, and session duration preferences.
2. **Validate & schedule** — Confirm the plan; a second step converts it to JSON, checks conflicts, and adds events to Google Calendar.

## Prerequisites

1. **Python 3.8+**
2. **OpenAI API key** — [platform.openai.com](https://platform.openai.com/api-keys)
3. **Google Calendar API credentials** — [OAuth quickstart](https://developers.google.com/calendar/api/quickstart/python)

## Setup

```bash
cd Sports-Sessions-Planner
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` in the project root:

```
OPENAI_API_KEY=your_openai_api_key_here
```

Optional:

```
TIMEZONE=Europe/Paris
GOOGLE_CALENDAR_IDS=primary,your-work-calendar-id@gmail.com
GOOGLE_WRITE_CALENDAR_ID=primary
```

### Multi-calendar (work + personal)

`GOOGLE_CALENDAR_IDS` lists calendars used for **busy-time detection** (comma-separated). Defaults to `primary` only.

`GOOGLE_WRITE_CALENDAR_ID` is where confirmed sessions are created (defaults to the first read calendar).

Use calendar IDs from the sidebar after OAuth (each connected calendar shows its name and whether it is used for read or write). A work calendar must be **visible to the Google account you authenticate with** — subscribe to or import it into that account first; an `@company.com` address alone is not enough if OAuth runs on a personal Gmail.

Example:

```
GOOGLE_CALENDAR_IDS=primary,abc123@group.calendar.google.com
GOOGLE_WRITE_CALENDAR_ID=primary
```

Place `credentials/credentials.json` from Google Cloud Console. On first calendar access, complete OAuth in the browser; `credentials/token.json` is saved automatically.

## Run (React UI + API)

Two terminals from the project root:

**1. API**

```bash
source venv/bin/activate
# If OpenAI calls fail behind a corporate proxy, clear proxy env for local dev:
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
export NO_PROXY="localhost,127.0.0.1,api.openai.com,.openai.com"
PYTHONPATH=src uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

Port 8000 already in use: `lsof -ti:8000 | xargs kill`

**2. Frontend**

```bash
cd frontend
npm install   # first time only
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` to the API on port 8000.

## Project layout

```
src/
  planner.py          # Chat + schedule logic (OpenAI, conflicts)
  google_calendar.py  # Google Calendar OAuth, read/write
  config.yaml         # Coach prompts
  server.py           # FastAPI routes (thin HTTP layer)
frontend/             # Vite + React UI
credentials/          # OAuth client + token (gitignored token)
```

## Using the interface

1. Set **rest day** and **typical session duration** in the sidebar.
2. Chat with the assistant about your training goals.
3. Click **Valider et planifier dans l'agenda** when the plan looks good.
4. Conflicting sessions are skipped (see the conflicts list if any).

## Tests

```bash
source venv/bin/activate
PYTHONPATH=src python3 src/tests/test_prompt_parameters.py
PYTHONPATH=src python3 src/tests/test_calendar_config.py
PYTHONPATH=src python3 src/tests/test_server_chat_stream.py
curl http://127.0.0.1:8000/api/health
```

See [docs/golden-path.md](docs/golden-path.md) for manual regression steps.
