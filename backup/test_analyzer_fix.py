from logic.analyzer import ProspectAnalyzer
import json

def test_analyzer_fix():
    print("Testing ProspectAnalyzer with fix...")
    analyzer = ProspectAnalyzer()
    
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
    
    print("Sending request...")
    result = analyzer.analyze_profile(mock_profile)
    
    print("\n--- Result ---")
    print(json.dumps(result, indent=2))
    
    if result.get("name") == "John Smith" and result.get("role") == "CTO":
        print("\nSUCCESS: Extracted correct data.")
    else:
        print("\nFAILURE: Did not extract correct data.")

if __name__ == "__main__":
    test_analyzer_fix()
