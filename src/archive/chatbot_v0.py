from openai import OpenAI
import streamlit as st
import os
from dotenv import load_dotenv
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import yaml
from pathlib import Path
from app.calendar import list_upcoming_events, add_sessions_to_calendar
import json
# from app.planner import generate_plan

# Load environment variables from .env file
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Streamlit app UX
st.title("📅 Calendar Manager — MVP")
tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "💬 Chat with recos", "📅 Planner", "🧠 Chat + Schedule"])

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

    #/*  
    # ============ Sidebar Configuration Settings ============
    # st.subheader("AI Model")
    # st.session_state["openai_model"] = st.selectbox(
    #     "Choose model",
    #     ["gpt-3.5-turbo", "gpt-4o-mini"],
    #     index=0,
    # )
    # temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.7)

    # st.subheader("Calendar Options")
    # avoid_conflicts = st.checkbox("Avoid conflicts with existing events", True)
    # preferred_time = st.radio("Preferred workout time", ["Morning", "Afternoon", "Evening"])

    # st.subheader("Preferences")
    # rest_day = st.selectbox("Preferred Rest Day", ["None", "Monday", "Friday", "Sunday"])
    # config_path = st.text_input("Config file path", "config/preferences.yaml")
    # ========================================================

    # st.divider()
    # if st.button("🗑️ Clear Chat History"):
    #    st.session_state.messages = []
    #    st.success("Chat cleared.")

    # ========================================================


# Load prompt instructions from the config file
PROMPTS_PATH = Path(__file__).parent / "app" / "config.yaml"
with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
    PROMPTS = yaml.safe_load(f)

# ---------------- Chat Tab ----------------
with tab1:
    st.header("💬 Build your training program")
    
    # Initialize session state
    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = "gpt-3.5-turbo"

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Create a container for messages to ensure proper layout
    messages_container = st.container()
    
    # Display previous messages in the container
    with messages_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
     # Chat input bar
    if prompt := st.chat_input("Type your training request..."):

        # Fill system prompt with sidebar prefs
        system_prompt = PROMPTS["base_system_prompt"].format(
            rest_day=rest_day,
            duration_min=duration_min,
        )

        # Always start fresh conversation with the system role
        st.session_state.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        # Display user message in the container
        with messages_container:

            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate response
            with st.chat_message("assistant"):
                stream = client.chat.completions.create(
                    model=st.session_state["openai_model"],
                    messages=[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ],
                    stream=True,
                )
                response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})

# ---------------- Chat Tab (with recommendations) ----------------
with tab2:
    st.header("💬 Build your training program (v2)")

    # Initialize session state
    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = "gpt-3.5-turbo"

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Display chat history
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- Recommended questions (suggestions) ---
    st.markdown("#### 🤔 Suggestions")
    cols = st.columns(3)
    suggestions = [
        "Summarize my week’s plan",
        "Give me recovery tips",
        "Suggest a new workout",
    ]
    for i, text in enumerate(suggestions):
        if cols[i].button(text):
            # Auto-fill the chat input with this suggestion
            st.session_state["prefill"] = text

    # --- Chat input (always at bottom) ---
    prompt = st.chat_input(
        "Type your message...",
        key="chat_input",
    )

    # If a suggestion button was clicked, use it as the prompt
    if "prefill" in st.session_state and st.session_state["prefill"]:
        prompt = st.session_state["prefill"]
        st.session_state["prefill"] = ""  # reset

    if prompt:
        # Save user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get assistant response (streamed)
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state["messages"]
                ],
                stream=True,
            )
            response = st.write_stream(stream)

        # Save assistant response
        st.session_state.messages.append({"role": "assistant", "content": response})


# ---------------- Planner Tab ----------------
with tab3:
    st.header("📅 Update your calendar")

    week_pick = st.date_input("Select target week", date.today())
    json_input = st.text_area(
            "Paste your training program", 
            placeholder="E.g. 'Run 3x, gym 2x this week...'")

    if st.button("🚀 Generate Plan"):
        if not json_input:
            st.warning("Please paste the generated plan in JSON format.")
        else:
            try:
                sessions = json.loads(json_input)

                # Optional: validate required keys in each session
                required_keys = {"date", "time", "duration_min", "title", "description"}
                for i, s in enumerate(sessions):
                    missing = required_keys - s.keys()
                    if missing:
                        st.error(f"Session #{i+1} is missing fields: {missing}")
                        st.stop()

                # Write to Google Calendar
                add_sessions_to_calendar(sessions)
                st.success(f"✅ {len(sessions)} session(s) added to Google Calendar.")
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
            except Exception as e:
                st.error(f"Error writing to calendar: {e}")
                st.exception(e)

    if st.button("🔐 Connect Google Calendar / Test"):
        try:
            events = list_upcoming_events(max_results=5)
            # st.write(events)  # debug print
            if not events:
                st.info("Connected ✅ but no upcoming events found.")
            else:
                st.success("Connected ✅. Here are your next events:")
                for e in events:
                    st.write(f"- **{e['summary']}** — {e['start']}")
        except Exception as err:
            st.error(f"Google Calendar connection failed: {err}")
            st.exception(err)  # show full traceback
            st.stop()

# ---------------- Chat + Schedule Tab (new) ----------------
with tab4:
    st.header("🧠 Plan a session and prepare to schedule")

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

    plain_text_system = (
        "You are a helpful training planner. Respond in plain text only, no JSON. "
        "Propose a clear, human-readable session or weekly plan with dates, times, "
        "durations, titles, and brief descriptions. Avoid any code blocks or JSON. "
        f"Assume today's date is {today_str} and interpret all relative dates (e.g., today, tomorrow, next Monday) relative to this date. "
        f"Weekly rest day: {rest_day}. Typical session duration: {duration_min} minutes. "
        "Critically: avoid conflicts with existing calendar events. Do not schedule overlapping times. "
        "If a requested time conflicts, propose the nearest available alternative that preserves spacing and recovery. "
        "Treat the following as hard busy intervals; do not overlap any: " + busy_context
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

    st.divider()
    st.info("This tab currently returns plain text only. After you validate, we'll convert and schedule in the next step.")

    st.divider()
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
        convert_system = (
            "Convert the user's last plan into a strict JSON array of sessions. "
            "JSON ONLY. No markdown or code fences. Schema per item: "
            "{ 'date': 'YYYY-MM-DD', 'time': 'HH:MM', 'duration_min': number, 'title': string, 'description': string }. "
            f"Assume today's date is {date.today().isoformat()} and interpret any relative dates accordingly. "
            "Ensure times avoid overlaps with these busy intervals (ISO): " + busy_context
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
