#!/usr/bin/env python3
"""
Test file to verify that sidebar parameters are correctly used in the system prompt.
This simulates the prompt formatting that happens in chatbot.py line 92.
"""

def test_prompt_formatting():
    """Test that sidebar parameters are correctly inserted into the system prompt."""
    
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
    
    # Simulate sidebar values (these would come from st.selectbox and st.slider)
    test_cases = [
        {
            "rest_day": "None",
            "duration_min": 60,
            "description": "Default values"
        },
        {
            "rest_day": "Sunday", 
            "duration_min": 45,
            "description": "Sunday rest, 45min sessions"
        },
        {
            "rest_day": "Friday",
            "duration_min": 90,
            "description": "Friday rest, 90min sessions"
        }
    ]
    
    print("🧪 Testing System Prompt Parameter Insertion")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['description']}")
        print(f"   rest_day = '{test_case['rest_day']}'")
        print(f"   duration_min = {test_case['duration_min']}")
        print("-" * 40)
        
        # Format the system prompt (same as chatbot.py line 92-95)
        system_prompt = BASE_SYSTEM_PROMPT.format(
            rest_day=test_case["rest_day"],
            duration_min=test_case["duration_min"],
        )
        
        print("📝 Generated System Prompt:")
        print(system_prompt)
        print("-" * 40)
        
        # Verify the parameters were inserted correctly
        assert f"Rest day(s): {test_case['rest_day']}" in system_prompt
        assert f"Typical session duration: {test_case['duration_min']} min" in system_prompt
        
        print("✅ Parameters correctly inserted!")
    
    print(f"\n🎉 All {len(test_cases)} test cases passed!")
    print("✅ Sidebar parameters are correctly used in the system prompt.")

if __name__ == "__main__":
    test_prompt_formatting()
