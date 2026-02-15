from logic.llm_client import KaggleClient
from logic.analyzer import ProspectAnalyzer
import json

def debug_full():
    print("Running full debug...")
    client = KaggleClient()
    analyzer = ProspectAnalyzer()
    
    mock_profile = """
    John Smith
    CTO at TechFlow Dynamics
    """
    
    # We will invoke the analyzer which calls client.chat
    # But we want to see what client.chat returns internally.
    # So we will monkeypatch client.generate or just call client.chat manually with the same prompt structure.
    
    system_prompt = "You are an expert sales researcher. Extract structured data from profiles into JSON."
    example_input = "Name: Sarah Jones\nRole: VP Marketing at CloudScale..."
    example_output = json.dumps({"name": "Sarah Jones", "role": "VP Marketing", "company": "CloudScale"})
    
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
    
    print("Sending prompt to LLM...")
    try:
        raw_response = client.chat(messages, max_new_tokens=500)
        
        with open("debug_log.txt", "w", encoding="utf-8") as f:
            f.write("=== RAW RESPONSE ===\n")
            f.write(raw_response)
            f.write("\n\n=== EXTRACTED JSON ===\n")
            extracted = client.extract_json(raw_response)
            f.write(json.dumps(extracted, indent=2) if extracted else "None")
            
        print("Debug log written to debug_log.txt")
        print(f"Extracted Name: {extracted.get('name') if extracted else 'None'}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_full()
