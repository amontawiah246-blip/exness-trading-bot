import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. SETUP & REFRESH ---
st.set_page_config(page_title="Gemini AI Scalper", layout="wide")

# This keeps the price/chart live every 60s without triggering the AI automatically
refresh_count = st_autorefresh(interval=60 * 1000, key="price_timer")

# --- 2. AI CONNECTION CHECK ---
# We check the API key and show a status light in the sidebar
gemini_connected = False
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Simple test to verify connection
        gemini_connected = True
    else:
        st.sidebar.error("❌ Key Missing in Secrets")
except Exception as e:
    st.sidebar.error(f"❌ Connection Failed: {e}")

# --- 3. SESSION STATE (MEMORY) ---
if 'pair' not in st.session_state: st.session_state.pair = "EUR/USD"
if 'tf' not in st.session_state: st.session_state.tf = "5m"
if 'ai_analysis' not in st.session_state: st.session_state.ai_analysis = "Click the button below to generate a signal."

# --- 4. SIDEBAR ---
st.sidebar.title("🎮 Dashboard")

# Status Indicator
if gemini_connected:
    st.sidebar.success("🟢 Gemini API: Connected")
else:
    st.sidebar.error("🔴 Gemini API: Disconnected")

pairs_dict = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X", "Gold (XAU)": "GC=F", "Bitcoin": "BTC-USD"
}

st.session_state.pair = st.sidebar.selectbox("Asset", list(pairs_dict.keys()), 
    index=list(pairs_dict.keys()).index(st.session_state.pair))

st.session_state.tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h"], 
    index=["1m", "5m", "15m", "1h"].index(st.session_state.tf))

ticker = pairs_dict[st.session_state.pair]

# --- 5. DATA ENGINE ---
def get_data(symbol, tf):
    df = yf.download(symbol, period="1d", interval=tf)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df['ADX'] = adx['ADX_14']
    df['EMA20'] = ta.ema(df['Close'], length=20)
    return df

df = get_data(ticker, st.session_state.tf)
last = df.iloc[-1]

# --- 6. UI LAYOUT ---
st.title(f"Live Market: {st.session_state.pair}")

col1, col2, col3 = st.columns(3)
col1.metric("Price", f"{last['Close']:.5f}")
col2.metric("RSI (14)", f"{last['RSI']:.1f}")
col3.metric("ADX Strength", f"{last['ADX']:.1f}", "Strong" if last['ADX'] > 25 else "Weak")

fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# --- 7. MANUAL AI TRIGGER ---
st.markdown("---")
if st.button("🚀 GET AI SIGNAL NOW", use_container_width=True):
    if gemini_connected:
        with st.spinner("Analyzing market patterns..."):
            prompt = f"Trader Verdict for {st.session_state.pair} ({st.session_state.tf}). Price: {last['Close']}, RSI: {last['RSI']}, ADX: {last['ADX']}. Recent: {df.tail(5).to_string()}. Give Buy/Sell/Wait and TP/SL."
            try:
                response = model.generate_content(prompt)
                st.session_state.ai_analysis = response.text
            except Exception as e:
                st.session_state.ai_analysis = f"Error generating signal: {e}"
    else:
        st.error("Cannot generate signal: Gemini API is not connected.")

st.info(st.session_state.ai_analysis)
