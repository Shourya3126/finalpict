import streamlit as st
import pandas as pd
import json
import logging
import os
import time
import re
import altair as alt  # For Analytics
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
    llm_url = st.text_input("Kaggle Endpoint URL", value="https://3944-34-187-196-159.ngrok-free.app")
    
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

tab1, tab2, tab3, tab4 = st.tabs(["📝 New Campaign", "🚀 Batch Processing (CSV)", "📚 Knowledge Base", "📊 Analytics"])

with tab1:
    st.subheader("Import Prospect Data")
    
    input_method = st.radio("Choose Input Method", ["LinkedIn URL", "Upload Resume/File", "Paste Text"], horizontal=True)
    
    raw_text = ""
    
    process_btn = False
    
    if input_method == "LinkedIn URL":
        url = st.text_input("Enter LinkedIn Profile URL")
        github_url = st.text_input("GitHub URL (Optional)")
        process_btn = st.button("Analyze Profile")
        
        if process_btn and url:
            # 1. Scrape LinkedIn
            with st.spinner("Scraping LinkedIn (this may take a moment)..."):
                scraper = WebScraper()
                raw_text = scraper.scrape_url(url)
                if "Error" in raw_text or "Auth Wall" in raw_text:
                    st.warning("Could not scrape fully. Please copy/paste the profile text/PDF if possible.")
                    st.text_area("Scraped Content (Debug)", raw_text, height=100)
                else:
                    st.success("Profile scraped successfully!")
            
            # 2. Scrape GitHub (if provided)
            if github_url:
                with st.spinner("Scanning GitHub projects..."):
                    try:
                        from logic.ingestion import GitHubScraper
                        gh_scraper = GitHubScraper()
                        projects = gh_scraper.scrape_user_projects(github_url, limit=1)
                        if projects:
                            st.success(f"Found latest project: {projects[0]['name']}")
                            st.session_state.github_projects = projects # Persist for generator
                            
                            raw_text += "\n\n[GitHub Projects Data]\n"
                            for p in projects:
                                raw_text += f"- Project Name: {p['name']}\n  Description/README: {p['description']}\n"
                    except Exception as e:
                        st.error(f"GitHub Error: {e}")

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
                
                # INJECT GITHUB DATA IMMEDIATELY
                if st.session_state.get("github_projects"):
                     analysis["github_projects"] = st.session_state.github_projects
                     # Append to key_insights for visibility
                     if "key_insights" not in analysis: analysis["key_insights"] = []
                     analysis["key_insights"].append(f"Active on GitHub: {st.session_state.github_projects[0]['name']}")
                
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
                    # Generate a unique suffix for keys
                    if "gen_id" not in st.session_state:
                         import uuid
                         st.session_state.gen_id = str(uuid.uuid4())
                    
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
            import random
            base_delay = 8 if total_rows > 10 else 5
            
            # Helper: Check if a value is garbage
            def is_garbage(val):
                if not val or val == "Unknown": return True
                v = val.strip()
                if "===" in v: return True
                if v.isdigit(): return True
                if len(v) < 2: return True
                return False

            # Helper: Sanitize a field
            def sanitize_field(value):
                if not value or value == "Unknown": return "Unknown"
                val = str(value)
                val = val.replace(chr(92) + 'n', chr(10))
                lines = [l.strip() for l in val.split(chr(10)) if l.strip()]
                if not lines: return "Unknown"
                clean_lines = [l for l in lines if not is_garbage(l)]
                if not clean_lines: return lines[-1] if lines else "Unknown"
                return clean_lines[0] if len(clean_lines) == 1 else clean_lines[-1]
            
            # Hallucination markers
            EXAMPLE_MARKERS = ["sarah jones", "sarah", "cloudscale"]
            
            def process_profile(scraper, analyzer, generator, target_url, my_offering, status_text, idx, total):
                status_text.text(f"Processing ({idx+1}/{total}): {target_url}...")
                
                # 1. Scrape
                raw_text = scraper.scrape_url(target_url)
                if "Auth Wall" in raw_text:
                    time.sleep(5)
                    raw_text = scraper.scrape_url(target_url)

                # 2. Clean text
                cleaned_text = scraper._filter_noise(raw_text)
                
                # 3. Failure detection
                if raw_text.strip().startswith("Error") or "Auth Wall" in raw_text or len(cleaned_text.strip()) < 50:
                    return {
                        "URL": target_url, "Name": "", "Company": "", "Role": "",
                        "Status": "Failed to Scrape"
                    }
                
                # 4. Analyze with Retry
                analysis = {}
                for attempt in range(2):
                    try:
                        analysis = analyzer.analyze_profile(cleaned_text)
                        if "error" not in analysis: break
                        time.sleep(2)
                    except:
                        time.sleep(2)
                
                if not analysis or "error" in analysis:
                    msgs = {}
                    status = "Failed Analysis"
                    analysis = {"name": "Unknown", "company": "Unknown", "role": "Unknown"}
                else:
                    similar = kb.find_similar(
                        company=analysis.get("company"),
                        industry=analysis.get("industry"),
                        role=analysis.get("role"),
                        offering=my_offering
                    )
                    msgs = generator.generate_campaign(analysis, my_offering, context_prospects=similar)
                    
                    if not msgs or (not msgs.get("email") and not msgs.get("linkedin")):
                        time.sleep(2)
                        msgs = generator.generate_campaign(analysis, my_offering, context_prospects=similar)

                # 7. Extract & sanitize fields
                name = sanitize_field(analysis.get("name") or "Unknown")
                company = sanitize_field(analysis.get("company") or "Unknown")
                role = sanitize_field(analysis.get("role") or "Unknown")
                
                status = "Success" if msgs else "Partial - Messages Empty"
                
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
                scraper.init_browser()
                for i, row in df.iterrows():
                    target_url = row[url_col]
                    try:
                        result = process_profile(scraper, analyzer, generator, target_url, my_offering, status_text, i, total_rows)
                        results.append(result)
                    except Exception as e:
                        results.append({"URL": target_url, "Status": f"Error: {str(e)}"})
                    progress_bar.progress((i + 1) / total_rows)
                        
            finally:
                scraper.close_browser()
                
            status_text.text("Batch Processing Complete!")
            
            # Auto-save
            saved_count = 0
            for r in results:
                if r.get("Status") == "Success" and r.get("Name") and r.get("Name") != "Unknown":
                    profile_for_kb = {"name": r.get("Name"), "company": r.get("Company"), "role": r.get("Role")}
                    msgs_for_kb = {"email": {"subject": r.get("Email Subject"), "body": r.get("Email Body")}, "linkedin": r.get("LinkedIn Msg")}
                    kb.save_prospect(profile_for_kb, messages=msgs_for_kb, url=r.get("URL"))
                    saved_count += 1
            
            if results:
                res_df = pd.DataFrame(results)
                st.dataframe(res_df)
                if saved_count > 0: st.success(f"📚 Auto-saved {saved_count} profiles")
                st.download_button("Download CSV", res_df.to_csv(index=False).encode('utf-8'), "results.csv", "text/csv")

with tab3:
    st.subheader("📚 Knowledge Base")
    
    stats = kb.get_stats()
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.metric("Total Prospects", stats["total"])
    col_s2.metric("Companies", stats["companies"])
    col_s3.metric("Industries", stats["industries"])
    
    data = kb.load_all()
    if data:
        display_data = []
        for p in data:
            # Calculate word count for email
            email_body = p.get("messages", {}).get("email", {}).get("body", "")
            word_count = len(email_body.split()) if email_body else 0
            
            display_data.append({
                "id": p.get("id", ""), 
                "Name": p.get("name", "Unknown"),
                "Company": p.get("company", "Unknown"),
                "Role": p.get("role", "Unknown"),
                "Industry": p.get("industry", "Unknown"),
                "Status": p.get("status", "Sent"),
                "Saved": p.get("timestamp", "")[:10] if p.get("timestamp") else "",
                "Has Messages": "✅" if p.get("messages") else "❌",
                "Email Words": word_count
            })
        
        kb_df = pd.DataFrame(display_data)
        
        # Configure columns
        column_config = {
            "id": None, # Hide ID
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=["Sent", "Opened", "Replied", "Meeting Booked", "Ghosted"],
                required=True,
                help="Update outreach status here"
            ),
            "Has Messages": st.column_config.TextColumn("Msgs", help="Messages generated?"),
            "Saved": st.column_config.TextColumn("Date"),
            "Email Words": st.column_config.NumberColumn("Email Words", help="Email body word count")
        }
        
        st.info("💡 Pro Tip: Edit the **Status** column directly in the table to update analytics!")
        
        edited_df = st.data_editor(
            kb_df,
            column_config=column_config,
            disabled=["Name", "Company", "Role", "Industry", "Saved", "Has Messages", "Email Words"],
            use_container_width=True,
            hide_index=True,
            key="kb_editor"
        )
        
        # Detect and Save Changes
        if not kb_df.equals(edited_df):
            # Create lookup for O(1) access
            id_to_index = {p["id"]: i for i, p in enumerate(data)}
            
            changes_count = 0
            for index, row in edited_df.iterrows():
                 pid = row["id"]
                 new_status = row["Status"]
                 
                 if pid in id_to_index:
                     idx = id_to_index[pid]
                     # Check if status changed
                     if data[idx].get("status", "Sent") != new_status:
                         data[idx]["status"] = new_status
                         changes_count += 1
            
            if changes_count > 0:
                kb.save_all(data)
                st.toast(f"✅ Updated {changes_count} prospect(s)!")
                time.sleep(1) # Brief pause to show toast before rerun
                st.rerun()
        
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

        # Practice Mode (Simulate Reply)
        st.divider()
        with st.expander("🤖 Practice Mode (Simulate Reply)"):
            st.info("Roleplay with the AI to test your messaging!")
            practice_names = [f"{p.get('name', 'Unknown')} — {p.get('company', '')}" for p in data]
            practice_sel = st.selectbox("Select prospect to simulate", practice_names, key="practice_select")
            
            if practice_sel:
                p_idx = practice_names.index(practice_sel)
                p_data = data[p_idx]
                
                # Get existing message
                saved_msg = ""
                msgs = p_data.get("messages", {})
                if msgs.get("email"):
                    saved_msg = f"Subject: {msgs['email'].get('subject', '')}\n\n{msgs['email'].get('body', '')}"
                elif msgs.get("linkedin"):
                    saved_msg = msgs["linkedin"]
                
                user_msg = st.text_area("Your Message (Edit to test variations)", value=saved_msg, height=200, key="practice_msg")
                
                c1, c2 = st.columns(2)
                tone = c1.select_slider("Prospect Mood", options=["Interested", "Curious", "Skeptical", "Busy", "Angry"], value="Skeptical")
                
                if st.button("Simulate Reply", type="primary"):
                    with st.spinner(f"Simulating {p_data.get('name')}..."):
                        # Initialize Client
                        from logic.llm_client import KaggleClient
                        # Use global llm_url from sidebar
                        client = KaggleClient(base_url=llm_url)
                        
                        prompt = f"""
                        [ROLEPLAY SIMULATION]
                        You are {p_data.get('name')}, {p_data.get('role')} at {p_data.get('company')}.
                        
                        SCENARIO: You just received this cold email:
                        "{user_msg}"
                        
                        YOUR TASK: Write ONLY the email reply body.
                        Tone: {tone}
                        Length: Under 50 words.
                        
                        CONSTRAINTS:
                        - Do NOT write "Here is a reply" or "Option 1".
                        - Do NOT offer multiple choices.
                        - Do NOT include a subject line.
                        - JUST write the reply text as if you hit 'Reply' and typed it.
                        """
                        
                        reply = client.generate(prompt, max_new_tokens=150)
                        
                        st.markdown(f"**📩 Reply from {p_data.get('name')}:**")
                        st.info(reply)
    else:
        st.info("No prospects saved yet. Process profiles to auto-populate the Knowledge Base.")

with tab4:
    st.header("📊 Campaign Analytics (Actual Data)")
    st.markdown("Metrics based on your tracked outreach results in the Knowledge Base.")
    
    # Load actual data
    kb_data = kb.load_all()
    
    if not kb_data:
        st.info("No data available yet. Save prospects and update their status in the Knowledge Base to see detailed analytics.")
    else:
        df = pd.DataFrame(kb_data)
        
        # Ensure status exists
        if "status" not in df.columns:
            df["status"] = "Sent"
        else:
            df["status"] = df["status"].fillna("Sent")
            
        # Calculate KPIs
        total_sent = len(df)
        replies = df[df["status"].isin(["Replied", "Meeting Booked"])].shape[0]
        # Assuming 'Opened' tag exists, or we count replies as opened too
        opens = df[df["status"].isin(["Opened", "Replied", "Meeting Booked"])].shape[0]
        
        reply_rate = (replies / total_sent * 100) if total_sent > 0 else 0.0
        open_rate = (opens / total_sent * 100) if total_sent > 0 else 0.0
        
        # KPI Display
        col1, col2, col3 = st.columns(3)
        col1.metric("Avg. Reply Rate", f"{reply_rate:.1f}%", help="Based on statuses: Replied, Meeting Booked")
        col2.metric("Open Rate", f"{open_rate:.1f}%", help="Based on statuses: Opened, Replied, Meeting Booked")
        col3.metric("Total Sent", f"{total_sent}", help="Total profiles in Knowledge Base")
        
        st.divider()
        
        # Funnel (Cumulative)
        # Opened = Opened + Replied + Booked + Ghosted
        # Replied = Replied + Booked + Ghosted
        opened_statuses = ["Opened", "Replied", "Meeting Booked", "Ghosted"]
        replied_statuses = ["Replied", "Meeting Booked", "Ghosted"]
        booked_statuses = ["Meeting Booked"]
        
        funnel_df = pd.DataFrame([
            {"Stage": "1. Sent (Total)", "Count": len(df)},
            {"Stage": "2. Opened (Cumulative)", "Count": len(df[df["status"].isin(opened_statuses)])},
            {"Stage": "3. Replied (Cumulative)", "Count": len(df[df["status"].isin(replied_statuses)])},
            {"Stage": "4. Meeting Booked", "Count": len(df[df["status"].isin(booked_statuses)])}
        ])
        
        c = alt.Chart(funnel_df).mark_bar().encode(
            x=alt.X('Stage', sort=["1. Sent (Total)", "2. Opened (Cumulative)", "3. Replied (Cumulative)", "4. Meeting Booked"]),
            y='Count',
            color=alt.value("#8b5cf6"),
            tooltip=['Stage', 'Count']
        ).interactive()
        
        st.altair_chart(c, use_container_width=True)
        
        st.divider()
        
        # Deep Dive Charts
        c1, c2 = st.columns(2)
        
        # Helper for reply boolean (Ghosted counts as a reply initially)
        df["is_reply"] = df["status"].isin(replied_statuses)
        
        with c1:
            st.subheader("📅 Activity (Daily Volume)")
            
            if "timestamp" in df.columns:
                try:
                    df["date_only"] = pd.to_datetime(df["timestamp"]).dt.date
                    daily_counts = df.groupby("date_only").size()
                    st.bar_chart(daily_counts, color="#2563eb")
                    st.caption("New prospects added per day.")
                except Exception as e:
                    st.error(f"Error parsing dates: {e}")
            else:
                st.info("No timestamp data available.")
                
        with c2:
            st.subheader("📏 Response by Length")
            # Calculate word count of saved email
            def get_word_count(row):
                msgs = row.get("messages", {})
                if isinstance(msgs, dict) and msgs.get("email"):
                    return len(msgs["email"].get("body", "").split())
                return 0
            
            df["word_count"] = df.apply(get_word_count, axis=1)
            
            email_df = df[df["word_count"] > 0].copy()
            
            if not email_df.empty:
                email_df["length_group"] = pd.cut(
                    email_df["word_count"], 
                    bins=[0, 50, 100, 9999], 
                    labels=["Short (<50)", "Medium (50-100)", "Long (>100)"]
                )
                len_perf = email_df.groupby("length_group")["is_reply"].mean() * 100
                st.bar_chart(len_perf, color="#10b981")
                st.caption("Does brevity lead to more replies?")
            else:
                st.info("No email data to analyze.")
