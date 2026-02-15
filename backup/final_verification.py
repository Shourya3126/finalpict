from logic.analyzer import ProspectAnalyzer
from logic.generator import MessageGenerator
import json
import time

def final_verification():
    print("=== FINAL VERIFICATION: End-to-End Test ===\n")
    
    analyzer = ProspectAnalyzer()
    generator = MessageGenerator()
    
    # 1. Mock Profile Input with Rich Details
    mock_input = """
    Jane Doe
    Head of Sales at StartupX
    
    Bio:
    Sales leader with a decade of experience in B2B SaaS. 
    Currently building a high-velocity sales team from scratch.
    Loves automated workflows, CRM hygiene, and cycling.
    
    Experience:
    - Head of Sales, StartupX (2021-Present)
    - Sales Manager, BigCorp (2015-2021)
    
    Education:
    - MBA, Harvard Business School
    - B.A. Economics, Yale
    
    Certifications:
    - Salesforce Certified Administrator
    - HubSpot Inbound Sales
    
    Recent Activity:
    - Shared a post about "The importance of empathy in cold calling".
    - Commented on a thread about AI in Sales.
    """
    
    print(f"--- 1. Analyzing Profile ({len(mock_input)} chars) ---")
    start_time = time.time()
    try:
        analysis_result = analyzer.analyze_profile(mock_input)
        print(f"Analysis completed in {time.time() - start_time:.2f}s")
        print(json.dumps(analysis_result, indent=2))
        
        # Verify Analysis
        if "education" in analysis_result and "certifications" in analysis_result:
            print("\n[SUCCESS] Analysis extracted detailed fields.\n")
        else:
            print("\n[FAILURE] Analysis missing new fields.\n")
            
    except Exception as e:
        print(f"\n[ERROR] Analysis crashed: {e}\n")
        return

    # 2. Generate Campaign
    offering = "We provide an AI-powered CRM that automates data entry."
    
    print(f"--- 2. Generating Campaign (Offering: {offering}) ---")
    start_time = time.time()
    try:
        campaign_result = generator.generate_campaign(analysis_result, offering)
        print(f"Generation completed in {time.time() - start_time:.2f}s")
        print(json.dumps(campaign_result, indent=2))
        
    except Exception as e:
        print(f"\n[ERROR] Generation crashed: {e}\n")

if __name__ == "__main__":
    final_verification()
