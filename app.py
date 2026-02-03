import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime

# --- SETUP ---
st.set_page_config(page_title="Pro-Signal AI", layout="wide")

# 1. Gemini Config (Make sure your key is in Streamlit Secrets)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except:
    st.error("API Key Missing! Add 'GEMINI_API_KEY' to Streamlit Secrets.")

# --- SIDEBAR: ASSET SELECTION ---
st.sidebar.title("💹 Multi-Platform Signals")
category = st.sidebar.selectbox("Market Type", ["Forex Majors", "Forex Minors", "Crypto/Gold"])

pairs = {
    "Forex Majors": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "AUD/USD": "AUDUSD=X"},
    "Forex Minors": {"EUR/GBP": "EURGBP=X", "GBP/JPY": "GBPJPY=X", "USD/ZAR": "USDZAR=X"},
    "Crypto/Gold": {"Gold": "GC=F", "Bitcoin": "BTC-USD"}
}

selected_label = st.sidebar.selectbox("Select Asset", list(pairs[category].keys()))
ticker = pairs[category][selected_label]
timeframe = st.sidebar.selectbox("Pocket Option Expiry / MT4 Chart", ["1m", "5m", "15m"])

# --- ENGINE ---
def get_pro_analysis(symbol, tf):
    # Fetch data (1m interval for scalping)
    df = yf.download(symbol, period="1d", interval=tf)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # Fast RSI for Pocket Option (7 instead of 14)
    df['RSI'] = ta.rsi(df['Close'], length=7)
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Technical Signal
    signal = "NEUTRAL"
    if last['RSI'] < 30: signal = "BUY (OVERSOLD)"
    elif last['RSI'] > 70: signal = "SELL (OVERBOUGHT)"
    
    return df, last, signal

# --- UI & AI EXECUTION ---
if st.sidebar.button("🚀 GENERATE PRO SIGNAL"):
    df, last_data, tech_signal = get_pro_analysis(ticker, timeframe)
    
    # 2. THE FULL GEMINI PRO PROMPT
    recent_history = df.tail(10).to_string() # Giving AI context of last 10 candles
    
    prompt = f"""
    You are a Master Price Action Trader for Pocket Option and MetaTrader.
    Asset: {selected_label} | Timeframe: {timeframe}
    Technical Signal: {tech_signal}
    Recent Data (OHLC):
    {recent_history}

    Your Task:
    1. Identify the nearest Support and Resistance based on these numbers.
    2. Look for patterns (Engulfing, Pin Bars, Doji).
    3. Give a final verdict: "HIGH CONFIDENCE BUY", "CAUTIOUS BUY", "WAIT", or "SELL".
    4. Limit your response to 3 clear bullet points.
    """
    
    st.markdown(f"## {selected_label} Analysis")
    
    with st.spinner("Gemini AI is analyzing candle patterns..."):
        response = model.generate_content(prompt)
        ai_verdict = response.text

    # Display Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Live Price", f"{last_data['Close']:.5f}")
    c2.metric("Fast RSI (7)", f"{last_data['RSI']:.1f}")
    c3.subheader(f"Signal: {tech_signal}")

    # Plotly Chart
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", height=400, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # Display AI Verdict
    st.info("🤖 **GEMINI PRO VERDICT**")
    st.write(ai_verdict)
