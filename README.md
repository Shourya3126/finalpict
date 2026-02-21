# 🚀 Cold Message Generator (AI-Powered Outreach)

An advanced AI tool designed to automate and personalize cold outreach at scale. It uses **LLMs (Llama-3 via Kaggle)** to analyze prospect profiles and generate hyper-personalized messages across 5 channels (Email, LinkedIn, WhatsApp, SMS, Instagram).

## ✨ Key Features

### 1. **Deep Profile Analysis**
- **LinkedIn Scraping**: Extracts experience, education, and recent posts to find "hooks".
- **GitHub Scanning (NEW)**: Scans a prospect's GitHub profile to read their top repositories and READMEs, enabling highly technical conversations.
- **Psychological Profiling**: Determines if a prospect is "Action-Oriented", "Relationship-Focused", or "Analytical" and adjusts the message tone accordingly.

### 2. **Smart Message Generation**
- **Multi-Channel**: Generates unique content for Email (Subject + Body), LinkedIn Connection Requests, WhatsApp, SMS, and Instagram DMs.
- **Social Proof Integration**: Automatically references similar prospects from your Knowledge Base (e.g., "We helped your peer at [Company X]...") to build trust.
- **A/B Testing**: Generate variant messages to test different angles (e.g., Value-first vs. Question-first).

### 3. **Knowledge Base & CRM**
- **Prospect Tracking**: Save generated profiles and messages to a local JSON database.
- **Status Management**: Track prospects through the funnel: `Sent` -> `Opened` -> `Replied` -> `Meeting Booked`.
- **Editable Table**: Update statuses directly in the UI.

### 4. **📊 Analytics Dashboard (NEW)**
- **Real-Time Funnel**: Visualize your conversion rates from Sent to Booked.
- **Daily Activity**: Track your outreach velocity over time.
- **Length Analysis**: See which email lengths (Short vs. Long) get better response rates.
- **Performance Metrics**: Auto-calculates Reply Rates and Open Rates based on your tracking.

### 5. **🤖 Practice Mode (NEW)**
- **AI Roleplay**: Simulate a conversation with your prospect *before* you reach out.
- **Persona Simulation**: The AI adopts the prospect's persona (role, company, mood) and replies to your draft message, helping you refine your pitch.

## 🛠️ Tech Stack
- **Frontend**: Streamlit
- **Visualization**: Altair (Interactive Charts)
- **Scraping**: Selenium (LinkedIn), BeautifulSoup (GitHub)
- **LLM**: Kaggle Model Endpoint (Llama-3-8b / Gemma)
- **Data**: JSON (Local Knowledge Base)

## 🚀 Setup & Usage

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the App**:
   ```bash
   streamlit run app.py
   ```
3. **Configure LLM**:
   - Enter your ngrok/Kaggle endpoint URL in the sidebar.
   
## 📈 Workflow
1. **Input**: Paste a LinkedIn URL (and optional GitHub URL).
2. **Analyze**: Click "Analyze Profile" to scrape and generate insights.
3. **Generate**: Review the 5-channel message drafts.
4. **Save**: Add to Knowledge Base.
5. **Track**: Update status in the "Knowledge Base" tab and view results in "Analytics".

---
This project is completely intended for demo and knowledge purpose


