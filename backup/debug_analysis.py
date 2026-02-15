from logic.llm_client import KaggleClient
from logic.analyzer import ProspectAnalyzer
import json

def debug_analyzer():
    print("Debugging ProspectAnalyzer...")
    analyzer = ProspectAnalyzer()
    
    # Real-ish profile text to test with
    mock_profile = """
    John Smith
    CTO at TechFlow Dynamics
    
    Summary:
    Experienced technology leader with 15 years in SaaS. Currently scaling an engineering team of 50+.
    Passionate about cloud architecture, AI integration, and developer productivity.
    Recently posted on LinkedIn about the struggles of migrating from AWS to GCP.
    
    Experience:
    - CTO, TechFlow Dynamics (2020-Present)
    - VP Engineering, SoftCorp (2015-2020)
    
    Education:
    M.S. Computer Science, MIT
    """
    
    print(f"\n--- Input Text ({len(mock_profile)} chars) ---\n{mock_profile}\n")
    
    # Few-Shot Prompt Strategy
    system_prompt = "You are an expert sales researcher. Extract structured data from profiles into JSON."

    example_input = """
    Name: Sarah Jones
    Role: VP Marketing at CloudScale
    Bio: 10 years driving growth for SaaS startups. Loves data-driven marketing and hiking.
    """

    example_output = json.dumps({
        "name": "Sarah Jones",
        "company": "CloudScale",
        "role": "VP Marketing",
        "industry": "SaaS / Technology",
        "seniority": "Executive",
        "psychological_profile": {
            "decision_authority": "High",
            "pain_points": ["Scaling growth", "Data analytics"],
            "goals": ["Drive revenue", "Brand awareness"],
            "communication_preference": "Data-driven"
        },
        "communication_style": {
            "formality": "Casual",
            "tone": "Enthusiastic",
            "vocabulary": "Simple"
        },
        "key_insights": ["Experienced in SaaS growth", "Outdoor enthusiast"],
        "personalization_hooks": ["Mention SaaS growth experience", "Ask about hiking trails"]
    })

    user_prompt = f"""
    EXAMPLE INPUT:
    {example_input}
    
    EXAMPLE JSON OUTPUT:
    {example_output}
    
    REAL INPUT:
    {mock_profile}
    
    REAL JSON OUTPUT:
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # Using the client directly to see raw output
    client = KaggleClient()
    try:
        print("Sending request to LLM...")
        raw_response = client.chat(messages, max_new_tokens=1500)
        print("\n--- RAW LLM RESPONSE ---\n")
        print(raw_response)
        print("\n------------------------\n")
        
        extracted = KaggleClient.extract_json(raw_response)
        print("Extracted JSON:")
        print(json.dumps(extracted, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_analyzer()
