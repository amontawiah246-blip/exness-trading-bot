import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import json

# --- 1. CONFIG ---
st.set_page_config(page_title="AI Trading Bot", layout="wide", page_icon="📈")
st_autorefresh(interval=60000, key="auto_refresh")

# --- 2. API CONNECTION CHECK ---
st.sidebar.header("🔌 Connection Status")

# Use st.secrets or a manual input for the key
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if not API_KEY:
    st.sidebar.error("❌ Missing API Key")
    st.sidebar.info("Add GEMINI_API_KEY to your Streamlit Secrets.")
    conn_ok = False
else:
    try:
        genai.configure(api_key=API_KEY)
        # Simple test call to verify connection
        model_test = genai.GenerativeModel('gemini-1.5-flash')
        st.sidebar.success("✅ Gemini: Connected")
        conn_ok = True
    except Exception as e:
        st.sidebar.error(f"❌ Connection Failed: {e}")
        conn_ok = False

# --- 3. SESSION STATE ---
if "signal_data" not in st.session_state:
    st.session_state.signal_data = None

# --- 4. DATA LOGIC ---
st.sidebar.divider()
ticker = st.sidebar.selectbox("Market Asset", ["EURUSD=X", "GBPUSD=X", "BTC-USD", "ETH-USD"])
timeframe = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h"])

@st.cache_data(ttl=60)
def load_market_data(t, i):
    data = yf.download(t, period="2d", interval=i)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data['RSI'] = ta.rsi(data['Close'], length=14)
    adx = ta.adx(data['High'], data['Low'], data['Close'])
    data = pd.concat([data, adx], axis=1)
    return data.dropna()

# --- 5. MAIN UI ---
df = load_market_data(ticker, timeframe)

if not df.empty:
    last_row = df.iloc[-1]
    
    st.title(f"🚀 {ticker} AI Trading Dashboard")
    
    # KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("Current Price", f"{last_row['Close']:.5f}")
    c2.metric("RSI (14)", f"{last_row['RSI']:.1f}")
    c3.metric("Trend (ADX)", f"{last_row['ADX_14']:.1f}")

    # Chart
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close']
    )])
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, b=0, t=0))
    st.plotly_chart(fig, use_container_width=True)

    # --- 6. ACTION CENTER (The Button) ---
    st.markdown("### 🤖 AI Command Center")
    btn_col, info_col = st.columns([1, 2])
    
    with btn_col:
        if st.button("🎯 GET REAL-TIME SIGNAL", use_container_width=True, type="primary", disabled=not conn_ok):
            if conn_ok:
                with st.spinner("Gemini is analyzing price action..."):
                    try:
                        ai_model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = f"Analyze {ticker} at price {last_row['Close']}. RSI is {last_row['RSI']}. ADX is {last_row['ADX_14']}. Provide a signal (BUY/SELL/WAIT) and a 1-sentence reason in JSON format: {{'signal': '...', 'reason': '...'}}"
                        response = ai_model.generate_content(prompt)
                        # Extract JSON
                        raw_text = response.text.strip().replace("```json", "").replace("```", "")
                        st.session_state.signal_data = json.loads(raw_text)
                    except Exception as e:
                        st.error(f"AI Error: {e}")

    # Display results
    if st.session_state.signal_data:
        res = st.session_state.signal_data
        st.info(f"**SIGNAL:** {res['signal']} | **WHY:** {res['reason']}")

else:
    st.warning("Waiting for market data... check your internet or ticker symbol.")
