import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import json
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. SETUP & REFRESH ---
st.set_page_config(page_title="Gemini 2.0 FX Scalper", layout="wide")
st_autorefresh(interval=60 * 1000, key="datarefresh") # Refresh price every 60s

# --- 2. API CONFIG ---
# Using the latest Gemini 2.0 Flash model
API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else "YOUR_KEY_HERE"
genai.configure(api_key=API_KEY)

# --- 3. SESSION STATE ---
if "ai_analysis" not in st.session_state:
    st.session_state.ai_analysis = {"signal": "WAIT", "confidence": 0, "reason": "Press the button."}

def get_ai_analysis(rsi, adx, close, ticker):
    # Updated to Gemini 2.0 Flash
    model = genai.GenerativeModel('gemini-2.0-flash-exp') 
    prompt = f"""
    Forex {ticker}: Price={close:.5f}, RSI={rsi:.2f}, ADX={adx:.2f}. 
    Return ONLY a JSON object:
    {{
        "signal": "BUY",
        "confidence": 85,
        "reason": "short explanation"
    }}
    """
    try:
        response = model.generate_content(prompt)
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except:
        return {"signal": "ERROR", "confidence": 0, "reason": "Check API connection."}

# --- 4. SIDEBAR ---
st.sidebar.title("🎮 Scalper Settings")
pair = st.sidebar.selectbox("Currency Pair", ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "BTC-USD"])
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h"], index=0) # Default to 1m

# --- 5. DATA ENGINE ---
fetch_p = "1d" if tf == "1m" else "5d"
data = yf.download(pair, period=fetch_p, interval=tf)

if not data.empty:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data['RSI'] = ta.rsi(data['Close'], length=14)
    adx_df = ta.adx(data['High'], data['Low'], data['Close'], length=14)
    data = pd.concat([data, adx_df], axis=1).dropna()
    
    if not data.empty:
        last = data.iloc[-1]
        
        # --- UI DISPLAY ---
        st.title(f"📊 {pair} Live Scalper")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Live Price", f"{last['Close']:.5f}")
        col2.metric("RSI (14)", f"{last['RSI']:.1f}")
        col3.metric("ADX (Trend)", f"{last['ADX_14']:.1f}")

        # --- CHARTING ---
        fig = go.Figure(data=[go.Candlestick(
            x=data.index,
            open=data['Open'], high=data['High'],
            low=data['Low'], close=data['Close'],
            name="Candlesticks"
        )])
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- AI SIGNAL ---
        if st.button("🚀 GET AI SIGNAL (GEMINI 2.0)", use_container_width=True):
            with st.spinner("Gemini 2.0 is reading the market..."):
                st.session_state.ai_analysis = get_ai_analysis(last['RSI'], last['ADX_14'], last['Close'], pair)

        res = st.session_state.ai_analysis
        st.divider()
        
        # Signal Styling
        if res['signal'] == "BUY": st.success(f"### 📈 SIGNAL: {res['signal']} ({res['confidence']}%)")
        elif res['signal'] == "SELL": st.error(f"### 📉 SIGNAL: {res['signal']} ({res['confidence']}%)")
        else: st.warning(f"### ⚖️ SIGNAL: {res['signal']} ({res['confidence']}%)")
        
        st.info(f"**AI Logic:** {res['reason']}")
