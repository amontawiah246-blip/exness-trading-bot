import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import json
from datetime import datetime

# 1. API Configuration
API_KEY = "YOUR_GEMINI_API_KEY"
genai.configure(api_key=API_KEY)

# 2. Page Config
st.set_page_config(page_title="Gemini Live Scalper", layout="wide")

# Initialize Session State (This saves your signal during refreshes)
if "ai_analysis" not in st.session_state:
    st.session_state.ai_analysis = None
if "last_update" not in st.session_state:
    st.session_state.last_update = "Never"

def get_ai_analysis(rsi, adx, close, ticker):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Forex {ticker}: Price={close:.5f}, RSI={rsi:.2f}, ADX={adx:.2f}. Return ONLY JSON: {{"signal": "BUY/SELL/WAIT", "confidence": 0-100, "reason": "short"}}"
    try:
        response = model.generate_content(prompt)
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except:
        return {"signal": "WAIT", "confidence": 0, "reason": "AI Error"}

# 3. Sidebar UI
st.sidebar.header("🕹️ Control Panel")
pair = st.sidebar.selectbox("Currency Pair", ["EURUSD=X", "GBPUSD=X", "USDJPY=X"])
timeframe = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m"])

# AUTO-REFRESH TOGGLE
live_mode = st.sidebar.toggle("Enable Live Refresh (60s)")
if live_mode:
    st.info("🔄 Live Mode Active: Price updates every minute.")
    st.empty() # Placeholder for refresh logic
    st.rerun() if False else None # Note: In local dev, use streamlit_autorefresh for better timing

# 4. Main Logic
st.title(f"📊 {pair} Live Dashboard")
st.caption(f"Last data pull: {datetime.now().strftime('%H:%M:%S')}")

if st.button("🚀 GET NEW AI SIGNAL") or live_mode:
    # Fetch Data
    fetch_p = "1d" if timeframe == "1m" else "5d"
    data = yf.download(pair, period=fetch_p, interval=timeframe)
    
    if not data.empty:
        # Flatten Multi-Index
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Calculate Indicators
        data['RSI'] = ta.rsi(data['Close'], length=14)
        adx_df = ta.adx(data['High'], data['Low'], data['Close'], length=14)
        data = pd.concat([data, adx_df], axis=1).dropna()
        
        if not data.empty:
            last = data.iloc[-1]
            
            # Update AI Signal ONLY if button pressed or no signal exists
            if st.button("🚀 GET NEW AI SIGNAL") or st.session_state.ai_analysis is None:
                with st.spinner("AI Analyzing..."):
                    st.session_state.ai_analysis = get_ai_analysis(last['RSI'], last['ADX_14'], last['Close'], pair)
            
            # Display Real-Time Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Live Price", f"{last['Close']:.5f}")
            c2.metric("RSI", f"{last['RSI']:.2f}")
            c3.metric("ADX", f"{last['ADX_14']:.2f}")

            # Display AI Signal from Session State
            res = st.session_state.ai_analysis
            st.divider()
            
            if res['signal'] == "BUY": st.success(f"### 📈 {res['signal']} ({res['confidence']}%)")
            elif res['signal'] == "SELL": st.error(f"### 📉 {res['signal']} ({res['confidence']}%)")
            else: st.warning(f"### ⚖️ {res['signal']} ({res['confidence']}%)")
            
            st.info(f"**AI Reasoning:** {res['reason']}")
