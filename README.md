# Sports Calendar Manager

## 🎯 Goal

Build, test, and explore different approaches using AI agents to schedule my sports sessions


## Project Overview

This is a small desktop tool that converts **plain-text sports training programs** into structured sessions and schedules them directly into my **Google Calendar**, using preferences I have set.

It uses **a single AI model (via OpenAI API)** for parsing and planning, and Python logic for event creation


## MVP Core features 

1. **Text Input of Training Programs**
    - Users provide request to plan training sessions as plain text in the chat
2. **Agent Parsing & Planning**
    - The AI agent scans the agenda to find free slots
    - The agent schedules the training sessions in free slots using preferences, and sports logic (respect rest days, escalate intensity during the week..) 
    - Outputs a planned list of sessions with suggested scheduling.
    - Takes feedbacks from user and updates the sessions accordingly
3. **Calendar Integration**
    - Another AI agent converts the plain text list to JSON
    - It uses Python logic to add events to Google Agenda


## Long term ambition / ideas

- **Refined Interfaces**: design front ideas
- **New Input Types**: PDF, images, URLs, voice input (e.g input a race preparation program in pdf)
- **Integrations**: Export to Garmin, Strava, etc.
- **MCP server**: try existing MCP servers to replace the Python functions used to get and write events from and to google agenda

---

## 🚀 How to use it

### Prerequisites

1. **Python 3.8+** installed
2. **OpenAI API key** - Get one from [OpenAI](https://platform.openai.com/api-keys)
3. **Google Calendar API credentials** - Follow [Google's OAuth setup guide](https://developers.google.com/calendar/api/quickstart/python)

### Setup

1. **Clone and navigate to the project:**
   ```bash
   cd Sports-Sessions-Planner
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API keys:**
   - Create a `.env` file in the project root:
     ```
     OPENAI_API_KEY=your_openai_api_key_here
     ```
   
5. **Set up Google Calendar API:**
   - Place your `credentials.json` file in the `credentials/` folder
   - The app will automatically handle OAuth authentication on first run

### Running the application

1. **Start the Streamlit app:**
   ```bash
   streamlit run src/chatbot.py
   ```

2. **Open your browser** to the URL shown (typically `http://localhost:8501`)

### Using the interface

1. **Configure your preferences** in the sidebar:
   - Set your weekly rest day
   - Set your typical session duration

2. **Chat with the assistant:**
   - Describe your training goals in plain text (e.g., "I want to run 3 times this week, with one long run on Saturday")
   - The assistant will propose a schedule that avoids conflicts with your existing calendar events
   - You can ask for modifications or clarifications - the conversation history is maintained

3. **Validate and schedule:**
   - Once you're happy with the proposed plan, click "✅ Validate and schedule"
   - The app will convert the plan to structured format, check for conflicts, and add sessions to your Google Calendar
   - Conflicting sessions will be skipped with a warning

4. **Clear chat history** (optional):
   - Use the "🗑️ Clear Chat History" button in the sidebar to start a new conversation