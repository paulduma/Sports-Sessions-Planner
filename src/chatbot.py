from openai import OpenAI
import streamlit as st
import os
from dotenv import load_dotenv
from datetime import date
import yaml
from pathlib import Path
from app.calendar import list_upcoming_events

# Load environment variables from .env file
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Streamlit app UX
st.title("📅 Calendar Manager — MVP")
tab1, tab2, tab3 = st.tabs(["💬 Chat", "💬 Chat with recos", "📅 Planner"])

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
    st.text_area(
            "Paste your training program", 
            placeholder="E.g. 'Run 3x, gym 2x this week...'")

    if st.button("🚀 Generate Plan"):
        st.success("✅ Plan generated (placeholder)")

    if st.button("🔐 Connect Google Calendar / Test"):
        try:
            events = list_upcoming_events(max_results=5)
            if not events:
                st.info("Connected ✅ but no upcoming events found.")
            else:
                st.success("Connected ✅. Here are your next events:")
                for e in events:
                    st.write(f"- **{e['summary']}** — {e['start']}")
        except Exception as err:
            st.error(f"Google Calendar connection failed: {err}")
            st.stop()