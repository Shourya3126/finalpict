@echo off
echo ===================================================
echo      Advanced AI Outreach Assistant Launcher
echo ===================================================

echo.
echo 1. Installing Python dependencies...
pip install -r requirements.txt

echo.
echo 2. Starting Streamlit App...
echo ===================================================
echo App will open in your browser.
echo Using remote Kaggle Endpoint for LLM generation.
echo ===================================================
streamlit run app.py
pause
