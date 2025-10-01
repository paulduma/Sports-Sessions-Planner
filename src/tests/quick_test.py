#!/usr/bin/env python3
"""
Quick test to show how sidebar parameters are used in the system prompt.
"""

import yaml
from pathlib import Path

# Load config (same as chatbot.py line 64-66)
PROMPTS_PATH = Path(__file__).parent / "src" / "app" / "config.yaml"
with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
    PROMPTS = yaml.safe_load(f)

# Simulate sidebar values (from lines 23 and 30 in chatbot.py)
rest_day = "Sunday"        # From st.selectbox on line 23
duration_min = 75          # From st.slider on line 30

print("🔧 Sidebar Parameters:")
print(f"   rest_day = '{rest_day}'")
print(f"   duration_min = {duration_min}")
print("\n" + "="*50)

# Format system prompt (same as chatbot.py lines 92-95)
system_prompt = PROMPTS["base_system_prompt"].format(
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
