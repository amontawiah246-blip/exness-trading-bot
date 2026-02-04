import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
import json

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="AI Trader", layout="wide")

# CSS to make the button big and visible
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #00ff00;
        color: black;
        font-size: 20px;
        height: 3em;
        width: 100%;
        border-radius: 10px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. API & STATE SETUP ---
# Get key from secrets
API_KEY = st.secrets.get("GEMINI_API_KEY", "MISSING")

if "ai_signal" not in st.session_state:
    st.session_state.ai_signal = "No signal generated yet. Click the button below."

# --- 3. THE ACTION CENTER (Force displayed at the top) ---
st.title("🤖 Exness AI Signal Bot")

# API Status indicator
if API_KEY == "MISSING":
    st.error("⚠️ Gemini API Key not found in Streamlit Secrets!")
else:
    st.success("✔️ Gemini API is Configured")

# THE BUTTON - Placed here so it's always visible
if st.button("🎯 GENERATE AI TRADING SIGNAL"):
    with st.spinner("Analyzing Market..."):
        try:
            # 1. Get Data
            temp_df = yf.download("EURUSD=X", period="1d", interval="1m")
            if temp_df.empty:
                st.session_state.ai_signal = "Error: Could not fetch market data."
            else:
                # 2. Setup AI
                genai.configure(api_key=API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # 3. Ask AI
                price = temp_df['Close'].iloc[-1]
                prompt = f"Current EURUSD price is {price}. Give a 1-sentence trading advice."
                response = model.generate_content(prompt)
                st.session_state.ai_signal = response.text
        except Exception as e:
            st.session_state.ai_signal = f"Connection Error: {str(e)}"

# Display the result in a big box
st.info(f"**LATEST SIGNAL:** {st.session_state.ai_signal}")

# --- 4. CHART SECTION (Below the button) ---
st.divider()
st.subheader("📈 Live Market Preview")
try:
    chart_data = yf.download("EURUSD=X", period="1d", interval="5m")
    if not chart_data.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=chart_data.index,
            open=chart_data['Open'], high=chart_data['High'],
            low=chart_data['Low'], close=chart_data['Close']
        )])
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)
except:
    st.write("Chart temporarily unavailable.")
