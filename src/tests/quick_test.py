#!/usr/bin/env python3
"""
Quick test to show how sidebar parameters are used in the system prompt.
"""

# Base system prompt (legacy - kept for tests)
BASE_SYSTEM_PROMPT = """You are an expert sports training planner.

Task:
- Read the user's unstructured training request.
- Break it down into sessions with smart ordering, as a professional coach would do (sessions intensity and order must be optimal for performance)
- Fit sessions into the user's available slots, respecting preferences.

User preferences:
- Rest day(s): {rest_day}
- Typical session duration: {duration_min} min

Output format:
Return ONLY a JSON array. Each item must have:
  - "date": YYYY-MM-DD
  - "time": HH:MM (24h)
  - "duration_min": integer
  - "title": short session name
  - "description": short note (1 line max)

No explanations, no markdown, no extra text."""

# Simulate sidebar values (from lines 23 and 30 in chatbot.py)
rest_day = "Sunday"        # From st.selectbox on line 23
duration_min = 75          # From st.slider on line 30

print("🔧 Sidebar Parameters:")
print(f"   rest_day = '{rest_day}'")
print(f"   duration_min = {duration_min}")
print("\n" + "="*50)

# Format system prompt (same as chatbot.py lines 92-95)
system_prompt = BASE_SYSTEM_PROMPT.format(
    rest_day=rest_day,
    duration_min=duration_min,
)

print("📝 Final System Prompt:")
print(system_prompt)

# Verify parameters are included
print("\n🔍 Verification:")
if f"Rest day(s): {rest_day}" in system_prompt:
    print(f"✅ rest_day parameter '{rest_day}' correctly inserted")
else:
    print(f"❌ rest_day parameter '{rest_day}' NOT found")

if f"Typical session duration: {duration_min} min" in system_prompt:
    print(f"✅ duration_min parameter '{duration_min}' correctly inserted")
else:
    print(f"❌ duration_min parameter '{duration_min}' NOT found")
