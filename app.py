import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. SETUP ---
st.set_page_config(page_title="Gemini AI Scalper", layout="wide")
st_autorefresh(interval=60 * 1000, key="price_timer") # Auto-refresh prices

# --- 2. API CONNECTION CHECK ---
# Checking if the key exists in secrets
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ API Key missing! Go to Streamlit Cloud -> Settings -> Secrets and add GEMINI_API_KEY='your_key_here'")
    gemini_connected = False
else:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        gemini_connected = True
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        gemini_connected = False

# --- 3. SESSION STATE ---
if 'pair' not in st.session_state: st.session_state.pair = "EUR/USD"
if 'tf' not in st.session_state: st.session_state.tf = "5m"
if 'ai_analysis' not in st.session_state: st.session_state.ai_analysis = "No signal yet. Click the button below."

# --- 4. SIDEBAR ---
st.sidebar.title("🎮 Dashboard")
if gemini_connected:
    st.sidebar.success("🟢 Gemini: Connected")
else:
    st.sidebar.error("🔴 Gemini: Offline")

pairs_dict = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "Gold (XAU)": "GC=F", "Bitcoin": "BTC-USD"}
st.session_state.pair = st.sidebar.selectbox("Asset", list(pairs_dict.keys()), index=list(pairs_dict.keys()).index(st.session_state.pair))
st.session_state.tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h"], index=["1m", "5m", "15m", "1h"].index(st.session_state.tf))

# --- 5. DATA ENGINE ---
ticker = pairs_dict[st.session_state.pair]
df = yf.download(ticker, period="1d", interval=st.session_state.tf)
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df['RSI'] = ta.rsi(df['Close'], length=14)
df['ADX'] = ta.adx(df['High'], df['Low'], df['Close'], length=14)['ADX_14']

# --- 6. MAIN DISPLAY ---
st.title(f"📊 {st.session_state.pair} Scalper")

# Big Button right at the top
if st.button("🚀 GENERATE AI SIGNAL NOW", use_container_width=True):
    if gemini_connected:
        with st.spinner("AI is reading the tape..."):
            last = df.iloc[-1]
            prompt = f"Act as a pro trader. Pair: {st.session_state.pair}, Price: {last['Close']}, RSI: {last['RSI']}. Give a 3-sentence Buy/Sell/Wait verdict."
            response = model.generate_content(prompt)
            st.session_state.ai_analysis = response.text
    else:
        st.warning("API not connected. Check your Secrets.")

# AI Verdict Box
st.info(st.session_state.ai_analysis)

# Chart
fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)
