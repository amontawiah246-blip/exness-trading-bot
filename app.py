import streamlit as st
import yfinance as yf
import google.generativeai as genai
import plotly.graph_objects as go
import pandas_ta as ta
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="Gemini 2.0 Trader", layout="wide")

# Big Green Button Styling
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #00ff00; color: black; font-size: 20px;
        height: 3em; width: 100%; border-radius: 10px; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. API & MODEL SELECTOR ---
st.sidebar.title("🤖 Model Settings")
API_KEY = st.secrets.get("GEMINI_API_KEY", "MISSING")

# Here is the fix: We use the 2.0 Flash identifier
model_choice = st.sidebar.selectbox(
    "Select Model", 
    ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro"]
)

if "ai_signal" not in st.session_state:
    st.session_state.ai_signal = "Ready. Click below for a signal."

# --- 3. THE ACTION CENTER ---
st.title("📈 Live AI Market Analysis")

if API_KEY == "MISSING":
    st.error("❌ API Key Missing! Go to Streamlit Settings > Secrets.")
else:
    st.success(f"✔️ Connected to {model_choice}")

# THE BUTTON
if st.button("🎯 GENERATE AI TRADING SIGNAL"):
    with st.spinner(f"Querying {model_choice}..."):
        try:
            # 1. Fetch Data
            df = yf.download("EURUSD=X", period="1d", interval="1m")
            if df.empty:
                st.session_state.ai_signal = "Error: Market data unavailable."
            else:
                # 2. Configure AI
                genai.configure(api_key=API_KEY)
                model = genai.GenerativeModel(model_choice)
                
                # 3. Prepare Indicators for AI
                price = df['Close'].iloc[-1]
                rsi = ta.rsi(df['Close'], length=14).iloc[-1]
                
                prompt = f"""
                Act as a professional Forex trader. 
                Instrument: EURUSD
                Price: {price:.5f}
                RSI: {rsi:.2f}
                Give a clear BUY, SELL, or WAIT signal and one sentence of logic.
                """
                
                response = model.generate_content(prompt)
                st.session_state.ai_signal = response.text
        except Exception as e:
            st.session_state.ai_signal = f"❌ Model Error: {str(e)}"

# Output Area
st.info(f"**AI VERDICT:** \n\n {st.session_state.ai_signal}")

# --- 4. CHART ---
st.divider()
try:
    chart_df = yf.download("EURUSD=X", period="1d", interval="5m")
    fig = go.Figure(data=[go.Candlestick(
        x=chart_df.index, open=chart_df['Open'], 
        high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close']
    )])
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,b=0,t=0))
    st.plotly_chart(fig, use_container_width=True)
except:
    st.write("Chart data loading...")
