from logic.generator import MessageGenerator
from logic.llm_client import KaggleClient
import json

def debug_generator():
    print("Running generator debug...")
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
    
    # We want to see the RAW response.
    # We can't easily hook into generator without modifying it or using the client directly.
    # So let's use the client directly with the SAME prompt structure as generator.py
    
    client = KaggleClient()
    
    my_offering = "We offer AI vetting for remote engineers."
    
    system_prompt = f"""
    You are a world-class SDR and Copywriter.
    Your task is to generate hyper-personalized outreach messages.
    
    OFFERING CONTEXT:
    "{my_offering}"
    
    RULES:
    1. No hallucinations.
    2. Reference specific profile details.
    3. Match tone.
    4. Clear CTA.
    """

    example_profile = json.dumps({
        "name": "Sarah Jones",
        "company": "CloudScale",
        "role": "VP Marketing",
        "psychological_profile": {"pain_points": ["Scaling growth"]},
        "key_insights": ["Loves hiking"],
        "personalization_hooks": ["Ask about hiking"]
    }, indent=2)

    example_output = json.dumps({
        "email": {
            "subject": "Scaling growth at CloudScale",
            "body": "Hi Sarah,\n\nSaw your post about hiking..."
        },
        "linkedin": "Hi Sarah, loved your post...",
        "whatsapp": "Hi Sarah...",
        "sms": "Sarah, quick question...",
        "instagram": "Hey Sarah...",
        "analysis": {
            "personalization_score": "9/10",
            "reasoning": "Strong hook."
        }
    }, indent=2)

    user_prompt = f"""
    EXAMPLE INPUT PROFILE:
    {example_profile}
    
    EXAMPLE JSON OUTPUT:
    {example_output}
    
    REAL INPUT PROFILE:
    {json.dumps(mock_profile, indent=2)}
    
    REAL JSON OUTPUT:
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    print("Sending prompt to LLM...")
    try:
        raw_response = client.chat(messages, max_new_tokens=1000)
        
        with open("debug_gen_log.txt", "w", encoding="utf-8") as f:
            f.write("=== RAW RESPONSE ===\n")
            f.write(raw_response)
            f.write("\n\n=== EXTRACTED JSON ===\n")
            extracted = client.extract_json(raw_response)
            f.write(json.dumps(extracted, indent=2) if extracted else "None")
            
        print("Debug log written to debug_gen_log.txt")
        if extracted:
            print(f"Extracted Keys: {list(extracted.keys())}")
        else:
            print("Failed to extract JSON")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_generator()
