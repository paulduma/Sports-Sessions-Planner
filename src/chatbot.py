from openai import OpenAI
import streamlit as st
import os
from dotenv import load_dotenv
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import yaml
from app.calendar import list_upcoming_events, add_sessions_to_calendar
import json

# Load environment variables from .env file
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load prompt instructions from the config file
PROMPTS_PATH = Path(__file__).parent / "app" / "config.yaml"
with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
    PROMPTS = yaml.safe_load(f)

# Streamlit app UX
st.title("🏋️ Calendar Manager — MVP")
main_container = st.container()

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("⚙️ Settings")

    st.subheader("Preferences")
    rest_day = st.selectbox(
        "Weekly rest day",
        ["None", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        index=0,
        key="rest_day_selector"
    )

    duration_min = st.slider(
        "Typical session duration (min)",
        min_value=20, max_value=150, value=60, step=10,
        key="duration_slider"
    )

    st.divider()

    if st.button("🗑️ Clear Chat History"):
        st.session_state["messages_tab4"] = []
        st.success("Chat cleared.")

# ---------------- Chat + Schedule (single interface) ----------------
with main_container:
    st.header("📝 Plan a session and prepare to schedule")

    # Initialize isolated state for this tab
    if "messages_tab4" not in st.session_state:
        st.session_state["messages_tab4"] = []
    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = "gpt-3.5-turbo"

    # Build a system prompt tailored for plain-text output only and date anchoring
    today_str = date.today().isoformat()

    # Try to fetch upcoming events to provide conflict context (structured intervals)
    calendar_busy_intervals = []
    try:
        upcoming = list_upcoming_events(max_results=50)
        for e in upcoming or []:
            start_info = e.get("start")
            end_info = e.get("end")
            if start_info and end_info:
                calendar_busy_intervals.append({
                    "start": start_info,
                    "end": end_info,
                })
    except Exception as _err:
        # If calendar isn't connected, proceed without busy context
        calendar_busy_intervals = []

    # Render as a compact JSON-like string for the model to reason over
    if calendar_busy_intervals:
        intervals_str = ", ".join([
            f"{{'start': '{it['start']}', 'end': '{it['end']}'}}" for it in calendar_busy_intervals
        ])
        busy_context = f"[{intervals_str}]"
    else:
        busy_context = "[]"

    # Load system prompt from config.yaml and fill in variables
    plain_text_system = PROMPTS["plain_text_system_prompt"].format(
        today_str=today_str,
        rest_day=rest_day,
        duration_min=duration_min,
        busy_context=busy_context
    )

    # Create a container so messages render above the input
    messages_container_tab4 = st.container()

    # Render history inside the container (keeps input at the bottom)
    with messages_container_tab4:
        for message in st.session_state["messages_tab4"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat input stays visually at the bottom
    prompt_tab4 = st.chat_input("Describe what you want to schedule...", key="chat_input_tab4")

    if prompt_tab4:
        # Rebuild the messages for the API call to ensure system is first
        api_messages = [
            {"role": "system", "content": plain_text_system},
            {"role": "user", "content": prompt_tab4},
        ]

        # Save and display user message inside container
        st.session_state["messages_tab4"].append({"role": "user", "content": prompt_tab4})
        with messages_container_tab4:
            with st.chat_message("user"):
                st.markdown(prompt_tab4)

            # Get assistant response (plain text) and display in container
            with st.chat_message("assistant"):
                stream = client.chat.completions.create(
                    model=st.session_state["openai_model"],
                    messages=api_messages,
                    stream=True,
                )
                response_text = st.write_stream(stream)

        st.session_state["messages_tab4"].append({"role": "assistant", "content": response_text})

    if st.button("✅ Validate and schedule"):
        # Find latest assistant message
        last_assistant = None
        for m in reversed(st.session_state["messages_tab4"]):
            if m["role"] == "assistant":
                last_assistant = m["content"]
                break
        if not last_assistant:
            st.warning("No assistant reply to validate. Ask for a plan first.")
            st.stop()

        # Conversion: instruct model to emit strict JSON sessions array
        convert_system = PROMPTS["convert_system_prompt"].format(
            today_str=date.today().isoformat(),
            busy_context=busy_context
        )

        convert_messages = [
            {"role": "system", "content": convert_system},
            {"role": "user", "content": last_assistant},
        ]

        try:
            conv = client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=convert_messages,
                stream=False,
            )
            raw = conv.choices[0].message.content
            # Sometimes models wrap JSON in code fences; strip common wrappers
            raw = raw.replace("```", "").strip()
            sessions = json.loads(raw)
        except Exception as err:
            st.error(f"Failed to convert to JSON sessions: {err}")
            st.stop()

        # Validate required keys and types
        required_keys = {"date", "time", "duration_min", "title", "description"}
        valid_sessions = []
        for i, s in enumerate(sessions if isinstance(sessions, list) else []):
            missing = required_keys - set(s.keys())
            if missing:
                st.warning(f"Session #{i+1} missing fields: {missing}; skipping")
                continue
            valid_sessions.append(s)

        if not valid_sessions:
            st.warning("No valid sessions found to schedule.")
            st.stop()

        # Server-side conflict check against upcoming events
        try:
            busy = list_upcoming_events(max_results=250)
        except Exception as err:
            busy = []

        LOCAL_TZ = ZoneInfo("Europe/Paris")

        def parse_iso_dt(value: str) -> datetime:
            # Supports both dateTime and all-day date
            if len(value) == 10:
                # all-day; treat as full-day busy starting midnight local time
                return datetime.fromisoformat(value + "T00:00:00").replace(tzinfo=LOCAL_TZ)
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            # Ensure timezone-aware; assume local tz if missing
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=LOCAL_TZ)
            # Convert to local tz for consistent comparisons
            return dt.astimezone(LOCAL_TZ)

        busy_intervals = []
        for e in busy:
            s = e.get("start")
            t = e.get("end")
            if not s or not t:
                continue
            try:
                s_dt = parse_iso_dt(s)
                t_dt = parse_iso_dt(t)
                busy_intervals.append((s_dt, t_dt))
            except Exception:
                continue

        def to_session_interval(sess: dict) -> tuple:
            start_str = f"{sess['date']}T{sess['time']}:00"
            start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=LOCAL_TZ)
            end_dt = start_dt + timedelta(minutes=int(sess["duration_min"]))
            return start_dt, end_dt

        def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
            return a_start < b_end and b_start < a_end

        non_conflicting = []
        conflicting = []
        for sess in valid_sessions:
            s_dt, e_dt = to_session_interval(sess)
            has_conflict = any(overlaps(s_dt, e_dt, b0, b1) for (b0, b1) in busy_intervals)
            if has_conflict:
                conflicting.append(sess)
            else:
                non_conflicting.append(sess)

        if conflicting:
            st.warning(f"Skipping {len(conflicting)} session(s) due to conflicts.")
            with st.expander("View conflicts"):
                for c in conflicting:
                    st.write(f"- {c['title']} on {c['date']} at {c['time']} ({c['duration_min']} min)")

        if not non_conflicting:
            st.info("No sessions to add after conflict filtering.")
            st.stop()

        try:
            add_sessions_to_calendar(non_conflicting)
            st.success(f"✅ Scheduled {len(non_conflicting)} session(s) to Google Calendar.")
        except Exception as err:
            st.error(f"Failed to write to calendar: {err}")