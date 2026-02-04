import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import json
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. SETUP & REFRESH ---
st.set_page_config(page_title="Gemini Live Scalper", layout="wide")

# This refreshes the whole page every 60 seconds automatically
st_autorefresh(interval=60 * 1000, key="datarefresh")

# --- 2. API CONFIG ---
# It's better to use Streamlit Secrets, but you can paste your key here
API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else "YOUR_KEY_HERE"
genai.configure(api_key=API_KEY)

# --- 3. SESSION STATE (Memory) ---
if "ai_analysis" not in st.session_state:
    st.session_state.ai_analysis = {"signal": "WAIT", "confidence": 0, "reason": "Press the button for a signal."}

# --- 4. AI LOGIC (Syntax Fix Applied) ---
def get_ai_analysis(rsi, adx, close, ticker):
    model = genai.GenerativeModel('gemini-1.5-flash')
    # Note: We use double {{ }} so Python doesn't confuse them with variables
    prompt = f"""
    Forex {ticker}: Price={close:.5f}, RSI={rsi:.2f}, ADX={adx:.2f}. 
    Return ONLY a JSON object exactly like this:
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
    except Exception as e:
        return {"signal": "ERROR", "confidence": 0, "reason": f"AI Error: {str(e)}"}

# --- 5. SIDEBAR ---
st.sidebar.title("🎮 Settings")
pair = st.sidebar.selectbox("Currency Pair", ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"])
tf = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h"], index=1)

# --- 6. MAIN DASHBOARD ---
st.title(f"📊 {pair} Scalper Dashboard")
st.caption(f"Last Price Update: {datetime.now().strftime('%H:%M:%S')}")

# Fetch Data
fetch_p = "1d" if tf == "1m" else "5d"
data = yf.download(pair, period=fetch_p, interval=tf)

if not data.empty:
    # Flatten MultiIndex Columns
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Calculate Indicators
    data['RSI'] = ta.rsi(data['Close'], length=14)
    adx_df = ta.adx(data['High'], data['Low'], data['Close'], length=14)
    data = pd.concat([data, adx_df], axis=1).dropna()
    
    if not data.empty:
        last = data.iloc[-1]
        
        # Display Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Live Price", f"{last['Close']:.5f}")
        c2.metric("RSI (14)", f"{last['RSI']:.1f}")
        c3.metric("ADX (Trend)", f"{last['ADX_14']:.1f}")

        st.divider()

        # AI SIGNAL BUTTON
        if st.button("🚀 GET AI SIGNAL", use_container_width=True):
            with st.spinner("AI is analyzing market patterns..."):
                st.session_state.ai_analysis = get_ai_analysis(last['RSI'], last['ADX_14'], last['Close'], pair)

        # SHOW AI VERDICT
        res = st.session_state.ai_analysis
        
        if res['signal'] == "BUY":
            st.success(f"### 📈 SIGNAL: {res['signal']} ({res['confidence']}%)")
        elif res['signal'] == "SELL":
            st.error(f"### 📉 SIGNAL: {res['signal']} ({res['confidence']}%)")
        else:
            st.warning(f"### ⚖️ SIGNAL: {res['signal']} ({res['confidence']}%)")
        
        st.info(f"**AI Analyst Reasoning:** {res['reason']}")
    else:
        st.error("Data received, but indicators are still calculating. Wait a moment.")
else:
    st.error("No data found. Check your internet or if the Forex market is open.")
