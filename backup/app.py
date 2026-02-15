import streamlit as st
import pandas as pd
import json
import logging
import os
import time
import re
from logic.ingestion import ResumeParser, WebScraper
from logic.analyzer import ProspectAnalyzer
from logic.generator import MessageGenerator
from logic.knowledge_base import KnowledgeBase

# Page Config
st.set_page_config(
    page_title="Local AI Outreach Assistant",
    page_icon="🚀",
    layout="wide"
)

# Custom CSS for "Premium" feel
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .main {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    h1 {
        color: #1e3a8a;
    }
    .stButton>button {
        background-color: #2563eb;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    llm_url = st.text_input("Kaggle Endpoint URL", value="https://edef-35-197-119-224.ngrok-free.app")
    
    if st.button("Test Connection"):
        try:
            from logic.llm_client import KaggleClient
            client = KaggleClient(base_url=llm_url)
            st.info("Sending test request...")
            res = client.generate("Test connection", max_new_tokens=5)
            if "Error" not in res:
                st.success(f"Connected! Response: {res}")
            else:
                st.error(f"Connection failed: {res}")
        except Exception as e:
            st.error(f"Connection failed: {e}")

# Initialize Logic
analyzer = ProspectAnalyzer(llm_url=llm_url)
generator = MessageGenerator(llm_url=llm_url)
kb = KnowledgeBase()

# Main Content
st.title("🚀 Autonomous Outreach Assistant")
st.markdown("Generate hyper-personalized cold outreach using your local AI.")

# Global Context (Your Offering)
with st.expander("💼 Your Offering / Context (Required to prevent hallucinations)", expanded=True):
    my_offering = st.text_area(
        "What are you selling / offering?", 
        value="We help companies scale their engineering teams with vetted AI talent.",
        placeholder="e.g. A new SaaS tool for social media scheduling..."
    )

tab1, tab2, tab3 = st.tabs(["📝 New Campaign", "🚀 Batch Processing (CSV)", "📚 Knowledge Base"])

with tab1:
    st.subheader("Import Prospect Data")
    
    input_method = st.radio("Choose Input Method", ["LinkedIn URL", "Upload Resume/File", "Paste Text"], horizontal=True)
    
    raw_text = ""
    
    process_btn = False
    
    if input_method == "LinkedIn URL":
        url = st.text_input("Enter LinkedIn Profile URL")
        process_btn = st.button("Analyze Profile")
        if process_btn and url:
            with st.spinner("Scraping LinkedIn (this may take a moment)..."):
                scraper = WebScraper()
                raw_text = scraper.scrape_url(url)
                if "Error" in raw_text or "Auth Wall" in raw_text:
                    st.warning("Could not scrape fully. Please copy/paste the profile text/PDF if possible.")
                    st.text_area("Scraped Content (Debug)", raw_text, height=100)
                else:
                    st.success("Profile scraped successfully!")

    elif input_method == "Upload Resume/File":
        uploaded_file = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])
        if uploaded_file:
            process_btn = st.button("Analyze File")
            if process_btn:
                file_type = uploaded_file.name.split('.')[-1].lower()
                with st.spinner("Parsing file..."):
                    raw_text = ResumeParser.extract_text(uploaded_file, file_type)
                    st.success("File parsed!")

    elif input_method == "Paste Text":
        col_paste, col_mock = st.columns([3, 1])
        with col_paste:
            raw_text = st.text_area("Paste Profile Text / Bio / Notes", height=200)
        with col_mock:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if st.button("🎲 Load Mock Profile"):
                raw_text = """
                Name: Sarah Chen
                Role: VP of Product at FinTech Solutions (Series B)
                About: 
                Passionate about building financial tools that actually help people. 
                Recently posted about the challenges of scaling remote product teams.
                Loves hiking and specialty coffee.
                Communication Style: Highly direct, uses emojis occasionally ☕️, focused on metrics and efficiency.
                Education: Stanford MBA.
                """
                st.session_state.raw_text_input = raw_text # Store if needed
                st.info("Mock data loaded. Click 'Analyze Text'.")
        
        process_btn = st.button("Analyze Text")

    # Analyze Button Logic
    if process_btn:
        if not raw_text:
            st.warning("Please provide input data.")
        # Logic Trigger
        if raw_text: # This implicitly means process_btn is also True because it's inside the outer if
            # Reset previous results to avoid stale data
            st.session_state.analysis_result = None
            st.session_state.generated_messages = None
            st.session_state.generated_messages_b = None
            
            with st.spinner("Analyzing Psychological Profile & Communication Style..."):
                analysis = analyzer.analyze_profile(raw_text)
                st.session_state.analysis_result = analysis
            
            # DEBUG: Show what we actually scraped to build trust
            with st.expander("🕵️‍♂️ Debug: Scraped Content (What the AI saw)", expanded=False):
                st.text_area("Raw Text", value=raw_text, height=150)

            if "error" not in analysis:
                # Check for similar prospects in KB
                company = analysis.get("company")
                industry = analysis.get("industry")
                role = analysis.get("role")
                
                # Query KB with offering-aware logic
                similar_prospects = kb.find_similar(
                    company=company, 
                    industry=industry, 
                    role=role, 
                    offering=my_offering
                )
                st.session_state.similar_prospects = similar_prospects
                
                with st.spinner(f"Generating Multi-Channel Campaigns (Found {len(similar_prospects)} similar profiles)..."):
                    messages = generator.generate_campaign(analysis, my_offering, context_prospects=similar_prospects)
                    
                    # Retry logic if generation fails (empty messages)
                    has_email = messages and messages.get("email", {}).get("body", "")
                    has_linkedin = messages and messages.get("linkedin", "")
                    
                    if not has_email and not has_linkedin:
                        st.warning("First attempt empty, retrying generation...")
                        time.sleep(2)
                        messages = generator.generate_campaign(analysis, my_offering, context_prospects=similar_prospects)
                    
                    st.session_state.generated_messages = messages
            else:
                st.error(f"Analysis Error: {analysis.get('error')}")

    # Display Results
    if st.session_state.get('analysis_result') and "error" not in st.session_state.analysis_result:
        st.divider()
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("🔍 Analysis")
            st.json(st.session_state.analysis_result)
            
            # Show Similar Prospects Context
            if st.session_state.get('similar_prospects'):
                st.info(f"💡 Context: Found {len(st.session_state.similar_prospects)} similar profiles in Knowledge Base. The AI used this success data.")
        
        with col2:
            st.subheader("✨ Generated Messages")
            
            # A/B Test Button
            if st.button("🔄 Generate A/B Variant"):
                 with st.spinner("Creating Variant B..."):
                    variant_msgs = generator.generate_campaign(
                        st.session_state.analysis_result, 
                        my_offering,
                        context_prospects=st.session_state.get('similar_prospects'),
                        variant_mode=True
                    )
                    st.session_state.generated_messages_b = variant_msgs
            
            # Show Messages (Tabs for A / B if exists)
            display_msgs = st.session_state.generated_messages
            if st.session_state.get('generated_messages_b'):
                st.warning("Displaying VARIANT B")
                display_msgs = st.session_state.generated_messages_b
                
            if display_msgs:
                # Check for error in generation
                if "error" in display_msgs:
                    st.error(f"Generation Error: {display_msgs['error']}")
                else:
                    # Generate a unique suffix for keys based on the analysis ID or timestamp
                    # We can use the prospect's name hash or a random token stored in session state
                    if "gen_id" not in st.session_state:
                         import uuid
                         st.session_state.gen_id = str(uuid.uuid4())
                    
                    # Update gen_id if we just generated new content (we can check if this is a fresh run)
                    # Actually, we set session_state.generated_messages in the logic block.
                    # We should also set a new gen_id there. 
                    # For now, let's just use a hash of the body content as part of the key to force update.
                    
                    c_email, c_li, c_wa, c_sms, c_insta = st.tabs(["Email", "LinkedIn", "WhatsApp", "SMS", "Instagram"])
                    
                    with c_email:
                        email_data = display_msgs.get("email", {})
                        if isinstance(email_data, dict):
                            s_key = f"subj_{hash(email_data.get('subject', ''))}"
                            b_key = f"body_{hash(email_data.get('body', ''))}"
                            
                            subj = st.text_input("Subject", value=email_data.get("subject", ""), key=s_key)
                            body = st.text_area("Body", value=email_data.get("body", ""), height=300, key=b_key)
                            
                            # Email Action
                            recipient_email = st.text_input("Recipient Email (Paste here)", key=f"rec_email_{s_key}")
                            if recipient_email and st.button("🚀 Send Email (Mailto)", key=f"btn_email_{s_key}"):
                                # Create Mailto Link
                                import urllib.parse
                                subject_enc = urllib.parse.quote(subj)
                                body_enc = urllib.parse.quote(body)
                                mailto_link = f"mailto:{recipient_email}?subject={subject_enc}&body={body_enc}"
                                st.markdown(f'<meta http-equiv="refresh" content="0;url={mailto_link}">', unsafe_allow_html=True)
                                st.success("Opened default mail client!")
                        else:
                            st.info(str(email_data))
                            
                    with c_li:
                        li_msg = display_msgs.get("linkedin", "")
                        final_li = st.text_area("Message", value=li_msg, height=200, key=f"li_{hash(li_msg)}")
                        
                        # LinkedIn Action
                        if st.button("🤖 Draft on LinkedIn (Auto-Type)", key=f"btn_li_{hash(li_msg)}"):
                            with st.spinner("Opening browser & typing..."):
                                # Use current scraping URL if valid
                                if "linkedin.com/in/" in url:
                                    scraper = WebScraper()
                                    res = scraper.draft_linkedin_message(url, final_li)
                                    st.success(res)
                                else:
                                    st.error("Invalid Profile URL for automation.")
                        
                    with c_wa:
                        wa_msg = display_msgs.get("whatsapp", "")
                        st.text_area("Message", value=wa_msg, height=150, key=f"wa_{hash(wa_msg)}")
                        
                    with c_sms:
                        sms_msg = display_msgs.get("sms", "")
                        st.text_area("Message", value=sms_msg, height=100, key=f"sms_{hash(sms_msg)}")
                        
                    with c_insta:
                        insta_msg = display_msgs.get("instagram", "")
                        final_insta = st.text_area("Message", value=insta_msg, height=150, key=f"insta_{hash(insta_msg)}")
                        
                        # Insta Action
                        insta_handle = st.text_input("Instagram Handle (e.g. zuck)", key=f"rec_insta_{hash(insta_msg)}")
                        if insta_handle and st.button("📸 Open DM", key=f"btn_insta_{hash(insta_msg)}"):
                            insta_url = f"https://www.instagram.com/{insta_handle}/"
                            st.markdown(f'<a href="{insta_url}" target="_blank">Click to Open Profile</a>', unsafe_allow_html=True)
                            st.info("Opened profile. Copy/Paste the message manually.")

                    st.info(f"Personalization Score: {display_msgs.get('analysis', {}).get('personalization_score', 'N/A')}")
                    
                    if st.button("Save to Knowledge Base"):
                        saved_url = url if input_method == "LinkedIn URL" else ""
                        kb.save_prospect(
                            st.session_state.analysis_result,
                            messages=display_msgs,
                            url=saved_url
                        )
                        st.success("✅ Saved to Knowledge Base with messages!")

with tab2:
    st.subheader("🚀 Batch Processing")
    
    st.info("Upload a CSV file containing a column named 'Linkedin URL' (or similar) to process multiple profiles at once.")
    
    batch_file = st.file_uploader("Upload CSV", type=["csv"])
    
    if batch_file:
        df = pd.read_csv(batch_file)
        st.dataframe(df.head())
        
        # Column selection
        cols = df.columns.tolist()
        url_col = st.selectbox("Select Column with LinkedIn URLs", cols, index=0 if "linkedin" in cols[0].lower() else 0)
        
        if st.button("Start Batch Processing"):
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            scraper = WebScraper()
            
            total_rows = len(df)
            
            # Use larger delays for big batches
            import random
            base_delay = 8 if total_rows > 10 else 5
            
            # Helper: Check if a value is garbage (section markers, etc.)
            def is_garbage(val):
                """Return True if value looks like scraping artifact, not real data."""
                if not val or val == "Unknown":
                    return True
                v = val.strip()
                if "===" in v:
                    return True
                if v.isdigit():
                    return True
                if len(v) < 2:
                    return True
                return False

            # Helper: Sanitize a field (remove multi-line junk)
            def sanitize_field(value):
                """Clean a field value: take only meaningful content."""
                if not value or value == "Unknown":
                    return "Unknown"
                val = str(value)
                # Always normalize: replace literal 2-char \n with real newline
                val = val.replace(chr(92) + 'n', chr(10))
                lines = [l.strip() for l in val.split(chr(10)) if l.strip()]
                if not lines:
                    return "Unknown"
                # Filter out garbage lines
                clean_lines = [l for l in lines if not is_garbage(l)]
                if not clean_lines:
                    return lines[-1] if lines else "Unknown"
                if len(clean_lines) == 1:
                    return clean_lines[0]
                return clean_lines[-1]
            
            # Hallucination markers from the example prompts
            EXAMPLE_MARKERS = ["sarah jones", "sarah", "cloudscale"]
            
            # Role keywords for field validation
            ROLE_KEYWORDS = [
                "developer", "engineer", "manager", "designer", "analyst", 
                "architect", "lead", "director", "vp", "intern", "student", 
                "consultant", "founder", "cto", "ceo", "scientist", 
                "specialist", "coordinator", "administrator", "associate", 
                "officer", "joiner", "trainee", "executive"
            ]
            
            def looks_like_role(text):
                """Returns True if text contains role-like keywords."""
                return any(kw in text.lower() for kw in ROLE_KEYWORDS)
            
            def looks_like_name(text):
                """Returns True if text looks like a person name (2-3 capitalized words, no role keywords)."""
                words = text.strip().split()
                if len(words) < 1 or len(words) > 5:
                    return False
                if looks_like_role(text):
                    return False
                # Most words should be capitalized
                cap_count = sum(1 for w in words if w[0].isupper())
                return cap_count >= len(words) * 0.5
            
            def check_msg_hallucination(msgs_dict):
                """Return True if messages reference the example profile."""
                if not msgs_dict:
                    return False
                all_text = json.dumps(msgs_dict).lower()
                return any(marker in all_text for marker in EXAMPLE_MARKERS)
            
            def extract_name_from_url(url):
                """Extract a name from the LinkedIn URL slug."""
                url_match = re.search(r'linkedin\.com/in/([^/]+)', url)
                if url_match:
                    slug = url_match.group(1)
                    # Remove trailing hash/ID (e.g., '-40842a1a2')
                    slug = re.sub(r'-[a-f0-9]{5,}$', '', slug)
                    slug = slug.replace('-', ' ').replace('/', '').strip()
                    # Remove any remaining trailing digits
                    slug = re.sub(r'\d+$', '', slug).strip()
                    if slug and len(slug) > 2:
                        return slug.title()
                return "Unknown"
            
            def extract_from_experience(cleaned_text):
                """Extract name, role, company directly from Experience section text."""
                hdr_name = "Unknown"
                hdr_role = "Unknown"
                hdr_company = "Unknown"
                
                # Name: first line after any section marker
                for marker in ["=== EXPERIENCE ===", "=== EDUCATION ===", "=== SKILLS ==="]:
                    match = re.search(re.escape(marker) + r'\s*\n\s*(.+)', cleaned_text)
                    if match:
                        candidate = match.group(1).strip()
                        if candidate and not is_garbage(candidate) and candidate not in ("Experience", "Education", "Skills", "Licenses & certifications"):
                            hdr_name = candidate
                            break
                
                # Company and Role: look for "Company · Full-time/Part-time/Internship" pattern
                exp_start = cleaned_text.find("=== EXPERIENCE ===")
                if exp_start >= 0:
                    exp_text = cleaned_text[exp_start:exp_start+1500]
                    company_match = re.search(
                        r'([A-Za-z0-9][A-Za-z0-9\s&.,\'\-]+?)\s*·\s*(?:Full-time|Part-time|Internship|Contract|Freelance|Apprenticeship)',
                        exp_text
                    )
                    if company_match:
                        hdr_company = company_match.group(1).strip()
                    
                    # Role: line immediately before the company line
                    exp_lines = exp_text.split('\n')
                    for i, eline in enumerate(exp_lines):
                        if '·' in eline and any(t in eline for t in ['Full-time', 'Part-time', 'Internship', 'Contract', 'Freelance', 'Apprenticeship']):
                            if i > 0:
                                role_candidate = exp_lines[i-1].strip()
                                if role_candidate and not is_garbage(role_candidate) and role_candidate != "Experience":
                                    hdr_role = role_candidate
                            break
                
                return hdr_name, hdr_role, hdr_company
            
            def process_profile(scraper, analyzer, generator, target_url, my_offering, status_text, idx, total):
                """Process a single profile. Returns a result dict."""
                status_text.text(f"Processing ({idx+1}/{total}): {target_url}...")
                
                # 1. Scrape
                raw_text = scraper.scrape_url(target_url)
                
                if "Auth Wall" in raw_text:
                    time.sleep(5)
                    raw_text = scraper.scrape_url(target_url)

                # 2. Clean text
                cleaned_text = scraper._filter_noise(raw_text)
                
                # 3. Failure detection
                has_useful_content = len(cleaned_text.strip()) > 50
                is_auth_wall = "Auth Wall" in raw_text
                is_error = raw_text.strip().startswith("Error")
                
                if is_error or is_auth_wall or not has_useful_content:
                    return {
                        "URL": target_url, "Name": "", "Company": "", "Role": "",
                        "Email Subject": "", "Email Body": "", "LinkedIn Msg": "",
                        "WhatsApp Msg": "", "SMS Msg": "",
                        "Status": "Failed to Scrape", "Data": cleaned_text[:200]
                    }
                
                # 4. Analyze with Retry
                analysis = {}
                analysis_error = None
                
                # Try up to 2 times
                for attempt in range(2):
                    try:
                        analysis = analyzer.analyze_profile(cleaned_text)
                        if "error" not in analysis:
                            break
                        analysis_error = analysis.get("error")
                        status_text.text(f"Analysis failed (attempt {attempt+1}), retrying...")
                        time.sleep(2)
                    except Exception as e:
                        analysis_error = str(e)
                        time.sleep(2)
                
                # If analysis failed completely
                if not analysis or "error" in analysis:
                    # Provide minimal fallback so we can at least save the scraped data
                    analysis = {
                        "name": "Unknown", 
                        "company": "Unknown", 
                        "role": "Unknown", 
                        "error": str(analysis_error or "Analysis Failed")
                    }
                    msgs = {} # Skip generation
                else:
                    # 5. Query KB for similar prospects (social proof context)
                    similar = kb.find_similar(
                        company=analysis.get("company"),
                        industry=analysis.get("industry"),
                        role=analysis.get("role"),
                        offering=my_offering
                    )
                    
                    # 6. Generate messages with KB context
                    msgs = generator.generate_campaign(analysis, my_offering, context_prospects=similar)
                    
                    # Check for empty messages and retry generation
                    has_email = msgs and msgs.get("email", {}).get("body", "")
                    has_linkedin = msgs and msgs.get("linkedin", "")
                    
                    if not has_email and not has_linkedin:
                        status_text.text(f"Retrying message generation ({idx+1}/{total})...")
                        time.sleep(5)
                        msgs = generator.generate_campaign(analysis, my_offering, context_prospects=similar)

                has_email = msgs and msgs.get("email", {}).get("body", "")
                has_linkedin = msgs and msgs.get("linkedin", "")
                
                # 6. Hallucination check for messages
                if check_msg_hallucination(msgs):
                    status_text.text(f"Detected example data in messages, regenerating ({idx+1}/{total})...")
                    time.sleep(5)
                    msgs = generator.generate_campaign(analysis, my_offering)
                    has_email = msgs and msgs.get("email", {}).get("body", "")
                    has_linkedin = msgs and msgs.get("linkedin", "")
                    if check_msg_hallucination(msgs):
                        msgs = {}
                        has_email = False
                        has_linkedin = False
                
                # 7. Extract & sanitize fields
                name = sanitize_field(analysis.get("name") or "Unknown")
                company = sanitize_field(analysis.get("company") or "Unknown")
                role = sanitize_field(analysis.get("role") or "Unknown")
                
                if is_garbage(name): name = "Unknown"
                if is_garbage(company): company = "Unknown"
                if is_garbage(role): role = "Unknown"
                
                # Reject hallucinated example values
                if name.lower() in EXAMPLE_MARKERS: name = "Unknown"
                if company.lower() in EXAMPLE_MARKERS: company = "Unknown"
                
                # 7.5 URL-BASED NAME CROSS-VALIDATION
                # If LLM name doesn't match URL slug at all, it came from sidebar
                url_name = extract_name_from_url(target_url)
                if name != "Unknown" and url_name != "Unknown":
                    url_parts = set(url_name.lower().split())
                    name_parts = set(name.lower().split())
                    if not url_parts.intersection(name_parts):
                        # Name is wrong - override from section header or URL
                        hdr_name, hdr_role, hdr_company = extract_from_experience(cleaned_text)
                        name = hdr_name if hdr_name != "Unknown" else url_name
                        # Company/role also likely wrong - override if we found better
                        if hdr_company != "Unknown":
                            company = hdr_company
                        if hdr_role != "Unknown":
                            role = hdr_role
                
                # 8. FIELD CROSS-VALIDATION
                # If company looks like a role title
                if company != "Unknown" and looks_like_role(company):
                    if role == "Unknown":
                        role = company
                        company = "Unknown"
                    elif not looks_like_role(role):
                        role = company
                        company = "Unknown"
                    elif looks_like_name(role):
                        # role is actually a name (e.g., "Nitish Chintakindi")
                        if name == "Unknown":
                            name = role
                        role = company
                        company = "Unknown"
                
                # If role looks like a person name, move to name
                if role != "Unknown" and name == "Unknown" and looks_like_name(role):
                    name = role
                    role = "Unknown"
                
                # 9. REGEX FALLBACKS
                if company == "Unknown" or role == "Unknown":
                    # Pattern 1: "Role at Company"
                    match = re.search(
                        r'([A-Za-z\s\-/]+(?:Developer|Engineer|Manager|Designer|Analyst|Consultant|Architect|Intern|Student|Lead|Director|VP|Founder))\s+at\s+([A-Za-z0-9\s\-&.]+)',
                        cleaned_text[:1000]
                    )
                    if match:
                        if role == "Unknown": role = match.group(1).strip()
                        if company == "Unknown": company = match.group(2).strip().split('\n')[0]
                    
                    # Pattern 2: "Role | Company"
                    if company == "Unknown":
                        match2 = re.search(r'([A-Za-z0-9\s\-]+)\s*\|\s*([A-Za-z0-9\s\-&.]+)', cleaned_text[:1000])
                        if match2:
                            if role == "Unknown": role = match2.group(1).strip()
                            company = match2.group(2).strip().split('\n')[0]
                    
                    # Pattern 3: Role keywords
                    if role == "Unknown":
                        role_match = re.search(
                            r'((?:Senior\s+|Junior\s+|Lead\s+|Full[\s-]?Stack\s+)?'
                            r'(?:Software|Java|Python|Backend|Frontend|Web|Data|Cloud|DevOps|ML|AI|System|Network|QA|Test|Mobile|iOS|Android)\s+'
                            r'(?:Developer|Engineer|Architect|Analyst|Scientist|Designer))',
                            cleaned_text[:1000], re.IGNORECASE
                        )
                        if role_match:
                            role = role_match.group(1).strip()
                    
                    # Pattern 4: Company from Experience section
                    if company == "Unknown":
                        exp_match = re.search(r'(?:EXPERIENCE|Experience).*?(?:at|·|-)\s*([A-Z][A-Za-z0-9\s&.]+?)(?:\n|$)', cleaned_text[:1500])
                        if exp_match:
                            company = exp_match.group(1).strip()
                
                # 10. Name fallback
                if name == "Unknown":
                    header_match = re.search(r'=== PROFILE HEADER ===\s*(.+)', cleaned_text)
                    if header_match:
                        candidate = header_match.group(1).strip().split('\n')[0]
                        if not is_garbage(candidate) and candidate.lower() not in EXAMPLE_MARKERS:
                            name = candidate
                
                if name == "Unknown":
                    name = extract_name_from_url(target_url)
                
                # 11. Determine status
                if has_email or has_linkedin:
                    status = "Success"
                else:
                    status = "Partial - Messages Empty"
                
                return {
                    "URL": target_url, "Name": name, "Company": company, "Role": role,
                    "Email Subject": msgs.get("email", {}).get("subject", "") if msgs else "",
                    "Email Body": msgs.get("email", {}).get("body", "") if msgs else "",
                    "LinkedIn Msg": msgs.get("linkedin", "") if msgs else "",
                    "WhatsApp Msg": msgs.get("whatsapp", "") if msgs else "",
                    "SMS Msg": msgs.get("sms", "") if msgs else "",
                    "Status": status
                }

            try:
                # Initialize ONE browser session for the entire batch
                status_text.text("Initializing browser session...")
                scraper.init_browser()
                
                # === MAIN PASS ===
                for i, row in df.iterrows():
                    target_url = row[url_col]
                    
                    # Randomized delay to avoid rate limiting
                    if i > 0:
                        delay = random.uniform(base_delay, base_delay + 4)
                        status_text.text(f"Waiting {delay:.0f}s before next profile...")
                        time.sleep(delay)

                    try:
                        result = process_profile(scraper, analyzer, generator, target_url, my_offering, status_text, i, total_rows)
                        results.append(result)
                    except Exception as e:
                        results.append({
                            "URL": target_url, "Name": "", "Company": "", "Role": "",
                            "Email Subject": "", "Email Body": "", "LinkedIn Msg": "",
                            "WhatsApp Msg": "", "SMS Msg": "",
                            "Status": f"Error: {str(e)}", "Data": ""
                        })
                    
                    progress_bar.progress((i + 1) / total_rows)
                
                # === RETRY PASS: Re-attempt failed / partial profiles ===
                failed_indices = [j for j, r in enumerate(results) 
                                  if r.get("Status", "").startswith(("Partial", "Failed", "Error"))]
                
                if failed_indices:
                    status_text.text(f"Retrying {len(failed_indices)} failed/partial profiles...")
                    time.sleep(3)
                    
                    for retry_idx, orig_idx in enumerate(failed_indices):
                        target_url = results[orig_idx]["URL"]
                        status_text.text(f"Retry ({retry_idx+1}/{len(failed_indices)}): {target_url}...")
                        
                        # Longer delay for retry pass
                        delay = random.uniform(10, 15)
                        time.sleep(delay)
                        
                        try:
                            retry_result = process_profile(
                                scraper, analyzer, generator, target_url, my_offering, 
                                status_text, retry_idx, len(failed_indices)
                            )
                            # Only replace if retry is better
                            retry_status = retry_result.get("Status", "")
                            orig_status = results[orig_idx].get("Status", "")
                            
                            if retry_status == "Success":
                                results[orig_idx] = retry_result
                            elif retry_status.startswith("Partial") and orig_status.startswith(("Failed", "Error")):
                                results[orig_idx] = retry_result
                        except Exception:
                            pass  # Keep original result
                        
            finally:
                scraper.close_browser()
                
            status_text.text("Batch Processing Complete!")
            
            # Auto-save successful profiles to Knowledge Base
            saved_count = 0
            for r in results:
                if r.get("Status") == "Success" and r.get("Name") and r.get("Name") != "Unknown":
                    profile_for_kb = {
                        "name": r.get("Name", ""),
                        "company": r.get("Company", ""),
                        "role": r.get("Role", ""),
                    }
                    msgs_for_kb = {
                        "email": {"subject": r.get("Email Subject", ""), "body": r.get("Email Body", "")},
                        "linkedin": r.get("LinkedIn Msg", ""),
                        "whatsapp": r.get("WhatsApp Msg", ""),
                        "sms": r.get("SMS Msg", ""),
                    }
                    kb.save_prospect(profile_for_kb, messages=msgs_for_kb, url=r.get("URL", ""))
                    saved_count += 1
            
            # Show Results
            if results:
                res_df = pd.DataFrame(results)
                st.dataframe(res_df)
                
                # Summary stats
                success_count = sum(1 for r in results if r.get("Status") == "Success")
                partial_count = sum(1 for r in results if r.get("Status", "").startswith("Partial"))
                failed_count = total_rows - success_count - partial_count
                st.info(f"✅ {success_count} Success | ⚠️ {partial_count} Partial | ❌ {failed_count} Failed")
                if saved_count > 0:
                    st.success(f"📚 Auto-saved {saved_count} successful profiles to Knowledge Base")
                
                # Download
                csv = res_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name='outreach_results.csv',
                    mime='text/csv',
                )

with tab3:
    st.subheader("📚 Knowledge Base")
    
    # Stats
    stats = kb.get_stats()
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.metric("Total Prospects", stats["total"])
    col_s2.metric("Companies", stats["companies"])
    col_s3.metric("Industries", stats["industries"])
    
    data = kb.load_all()
    if data:
        # Display as a clean table
        display_data = []
        for p in data:
            display_data.append({
                "Name": p.get("name", "Unknown"),
                "Company": p.get("company", "Unknown"),
                "Role": p.get("role", "Unknown"),
                "Industry": p.get("industry", "Unknown"),
                "Has Messages": "✅" if p.get("messages") else "❌",
                "URL": p.get("url", ""),
                "Saved": p.get("timestamp", "")[:10] if p.get("timestamp") else "",
                "_id": p.get("id", "")
            })
        
        kb_df = pd.DataFrame(display_data)
        st.dataframe(kb_df.drop(columns=["_id"]), use_container_width=True)
        
        # Delete functionality
        st.divider()
        with st.expander("🗑️ Delete a Prospect"):
            names_for_delete = [f"{p.get('name', 'Unknown')} — {p.get('company', '')}" for p in data]
            selected = st.selectbox("Select prospect to delete", names_for_delete)
            if st.button("Delete Selected", type="secondary"):
                idx = names_for_delete.index(selected)
                prospect_id = data[idx].get("id")
                if prospect_id:
                    kb.delete_prospect(prospect_id)
                    st.success(f"Deleted: {selected}")
                    st.rerun()
        
        # View details
        with st.expander("🔍 View Prospect Details"):
            names_for_view = [f"{p.get('name', 'Unknown')} — {p.get('company', '')}" for p in data]
            selected_view = st.selectbox("Select prospect to view", names_for_view, key="view_select")
            view_idx = names_for_view.index(selected_view)
            prospect = data[view_idx]
            
            st.json(prospect.get("profile", {}))
            
            saved_msgs = prospect.get("messages", {})
            if saved_msgs:
                st.markdown("**Saved Messages:**")
                if saved_msgs.get("email"):
                    st.text_area("Email", value=f"Subject: {saved_msgs['email'].get('subject', '')}\n\n{saved_msgs['email'].get('body', '')}", height=150, key=f"kb_email_{view_idx}")
                if saved_msgs.get("linkedin"):
                    st.text_area("LinkedIn", value=saved_msgs["linkedin"], height=100, key=f"kb_li_{view_idx}")
                if saved_msgs.get("whatsapp"):
                    st.text_area("WhatsApp", value=saved_msgs["whatsapp"], height=100, key=f"kb_wa_{view_idx}")
    else:
        st.info("No prospects saved yet. Process profiles to auto-populate the Knowledge Base.")
