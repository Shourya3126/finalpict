from logic.generator import MessageGenerator
import json

def test_generator_fix():
    print("Testing MessageGenerator with fix...")
    generator = MessageGenerator()
    
    mock_profile = {
        "name": "Sarah Chen",
        "role": "VP of Product",
        "company": "FinTech Solutions",
        "psychological_profile": {
            "pain_points": ["Scaling remote teams"],
            "communication_preference": "Direct"
        },
        "key_insights": ["Loves specialty coffee"],
        "personalization_hooks": ["Mention remote team scaling"]
    }
    
    print("Sending request...")
    result = generator.generate_campaign(mock_profile, "We offer AI vetting for remote engineers.")
    
    print("\n--- Result ---")
    print(json.dumps(result, indent=2))
    
    if "email" in result and "linkedin" in result:
        print("\nSUCCESS: Generated campaign.")
    else:
        print("\nFAILURE: Did not generate correct structure.")

if __name__ == "__main__":
    test_generator_fix()
