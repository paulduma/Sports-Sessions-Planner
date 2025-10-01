#!/usr/bin/env python3
"""
Test file to verify that sidebar parameters are correctly used in the system prompt.
This simulates the prompt formatting that happens in chatbot.py line 92.
"""

import yaml
from pathlib import Path

def test_prompt_formatting():
    """Test that sidebar parameters are correctly inserted into the system prompt."""
    
    # Load the config file (same as in chatbot.py)
    PROMPTS_PATH = Path(__file__).parent / "src" / "app" / "config.yaml"
    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        PROMPTS = yaml.safe_load(f)
    
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
        system_prompt = PROMPTS["base_system_prompt"].format(
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
