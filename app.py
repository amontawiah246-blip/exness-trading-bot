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

# Automatically refreshes the app every 60 seconds
refresh_count = st_autorefresh(interval=60 * 1000, key="trading_timer")

# --- 2. AI CONFIG (404 FIX) ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Using 'gemini-1.5-flash' (most stable name)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Missing GEMINI_API_KEY in Streamlit Secrets!")

# --- 3. SESSION STATE (MEMORY FIX) ---
# This prevents the app from resetting your pair and time on refresh
if 'pair' not in st.session_state:
    st.session_state.pair = "EUR/USD"
if 'tf' not in st.session_state:
    st.session_state.tf = "5m"

# --- 4. SIDEBAR CONTROLS ---
st.sidebar.title("🎮 Dashboard Controls")
st.sidebar.write(f"🔄 Refresh Count: {refresh_count}")
st.sidebar.caption(f"Last Sync: {datetime.now().strftime('%H:%M:%S')}")

pairs_dict = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "Gold (XAU)": "GC=F",
    "Bitcoin": "BTC-USD"
}

# Selectbox updates the session state directly
selected_label = st.sidebar.selectbox(
    "Asset", 
    list(pairs_dict.keys()), 
    index=list(pairs_dict.keys()).index(st.session_state.pair),
    key="pair_selector"
)
st.session_state.pair = selected_label

timeframe = st.sidebar.selectbox(
    "Timeframe", 
    ["1m", "5m", "15m", "1h"], 
    index=["1m", "5m", "15m", "1h"].index(st.session_state.tf),
    key="tf_selector"
)
st.session_state.tf = timeframe

ticker = pairs_dict[selected_label]

# --- 5. DATA & INDICATORS ---
def get_analysis_data(symbol, tf):
    df = yf.download(symbol, period="1d", interval=tf)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # RSI (Momentum)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    # ADX (Trend Strength)
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df['ADX'] = adx_df['ADX_14']
    # EMA (Trend Direction)
    df['EMA20'] = ta.ema(df['Close'], length=20)
    
    return df

# --- 6. MAIN UI ---
df = get_analysis_data(ticker, timeframe)
last = df.iloc[-1]

# Top Metric Row
m1, m2, m3, m4 = st.columns(4)
m1.metric("Live Price", f"{last['Close']:.5f}")
m2.metric("RSI (14)", f"{last['RSI']:.1f}")

# Trend Strength Logic
adx_val = last['ADX']
strength = "Weak"
if adx_val > 25: strength = "Strong"
if adx_val > 50: strength = "Extreme"
m3.metric("Trend Strength", f"{adx_val:.1f}", strength)

m4.metric("EMA 20", "Above" if last['Close'] > last['EMA20'] else "Below")

# Chart
fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

# --- 7. AUTOMATED AI VERDICT ---
st.markdown("---")
st.subheader("🤖 AI Technical Verdict")

with st.spinner("Gemini AI is analyzing patterns..."):
    # Send recent data to AI
    recent_data = df.tail(10).to_string()
    prompt = f"""
    Act as a professional Forex Scalper.
    Asset: {selected_label} | Timeframe: {timeframe}
    Current Price: {last['Close']} | RSI: {last['RSI']} | ADX Strength: {adx_val}
    
    Recent Data:
    {recent_data}
    
    Give a 3-sentence verdict:
    1. Market Sentiment (Bullish/Bearish)
    2. Entry Signal (Buy/Sell/Wait)
    3. Suggested Take Profit/Stop Loss
    """
    
    try:
        response = model.generate_content(prompt)
        st.info(response.text)
    except Exception as e:
        st.error(f"AI offline: {e}")
