import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import json
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. SETUP ---
st.set_page_config(page_title="Gemini 2.0 Scalper", layout="wide")
st_autorefresh(interval=60000, key="fxcp_refresh") # Auto-refresh UI every 60s

# --- 2. API CONFIG (Gemini 2.0 Flash) ---
API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else "YOUR_KEY_HERE"
genai.configure(api_key=API_KEY)

# --- 3. STATE MANAGEMENT ---
# This ensures the signal stays on screen even after the page refreshes
if "ai_signal" not in st.session_state:
    st.session_state.ai_signal = None

def fetch_gemini_signal(rsi, adx, price, ticker):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        # Using double {{ }} to fix the SyntaxError you had earlier
        prompt = f"""
        Act as a pro Forex Scalper. Analyze {ticker}: 
        Price: {price:.5f}, RSI: {rsi:.2f}, ADX: {adx:.2f}.
        Return ONLY JSON:
        {{ "signal": "BUY/SELL/WAIT", "conf": 0-100, "reason": "1 sentence" }}
        """
        response = model.generate_content(prompt)
        # Clean the response in case Gemini adds markdown backticks
        res_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(res_text)
    except Exception as e:
        return {"signal": "ERROR", "conf": 0, "reason": str(e)}

# --- 4. SIDEBAR ---
st.sidebar.header("📊 Market Selector")
ticker = st.sidebar.selectbox("Pair", ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "BTC-USD"])
timeframe = st.sidebar.selectbox("Interval", ["1m", "5m", "15m"], index=0)

# --- 5. DATA FETCHING ---
df = yf.download(ticker, period="1d", interval=timeframe)

if not df.empty:
    # Flatten columns if necessary
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Technical Indicators
    df['RSI'] = ta.rsi(df['Close'], length=14)
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx_df], axis=1).dropna()
    
    last_row = df.iloc[-1]
    
    # --- 6. DASHBOARD UI ---
    st.title(f"🚀 {ticker} Live Analysis")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Price", f"{last_row['Close']:.5f}")
    m2.metric("RSI", f"{last_row['RSI']:.1f}")
    m3.metric("Trend (ADX)", f"{last_row['ADX_14']:.1f}")

    # Plot Chart
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(darkmode=True, height=400, margin=dict(l=10, r=10, b=10, t=10))
    st.plotly_chart(fig, use_container_width=True)

    # --- 7. THE SIGNAL BUTTON ---
    st.write("---")
    if st.button("🎯 GET AI TRADING SIGNAL", use_container_width=True, type="primary"):
        with st.spinner("Gemini 2.0 is calculating..."):
            st.session_state.ai_signal = fetch_gemini_signal(
                last_row['RSI'], last_row['ADX_14'], last_row['Close'], ticker
            )

    # Display the Result
    if st.session_state.ai_signal:
        sig = st.session_state.ai_signal
        color = "green" if sig['signal'] == "BUY" else "red" if sig['signal'] == "SELL" else "gray"
        
        st.markdown(f"""
        <div style="padding:20px; border-radius:10px; border: 2px solid {color}; background-color: rgba(0,0,0,0.1)">
            <h2 style="color:{color}; margin:0;">{sig['signal']} ({sig['conf']}%)</h2>
            <p style="font-size:1.2rem;"><strong>Reason:</strong> {sig['reason']}</p>
        </div>
        """, unsafe_allow_index=True)

else:
    st.error("Waiting for Market Data...")
