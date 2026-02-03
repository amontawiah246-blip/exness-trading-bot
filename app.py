import streamlit as st
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime

# 1. SECURE API SETUP
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.warning("⚠️ API Key not found in Secrets. Please add it to your Streamlit Settings.")

# 2. UI DESIGN
st.set_page_config(page_title="Gemini Quant Pro", layout="wide")
st.markdown("<style>.stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #333; }</style>", unsafe_allow_html=True)

# 3. MARKET DATA ENGINE
def get_analysis(ticker):
    df = yf.download(ticker, period="1d", interval="1m", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    df.ta.rsi(append=True)
    df.ta.bbands(append=True)
    
    # Identify Signal
    last = df.iloc[-1]
    price = last['Close']
    rsi = last.filter(like='RSI').iloc[0]
    bbl = last.filter(like='BBL').iloc[0]
    bbu = last.filter(like='BBU').iloc[0]
    
    signal, color, arrow = "NEUTRAL", "gray", "▬"
    if price <= bbl: signal, color, arrow = "BUY", "#00ffcc", "▲"
    elif price >= bbu: signal, color, arrow = "SELL", "#ff4b4b", "▼"
    
    return df, price, rsi, signal, color, arrow

# 4. DASHBOARD BODY
st.title("💎 Gemini Quant Pro")
ticker = st.sidebar.selectbox("Market", ["EURUSD=X", "GBPUSD=X", "BTC-USD"])

if st.sidebar.button("GET LIVE SIGNAL"):
    df, price, rsi, signal, color, arrow = get_analysis(ticker)
    
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Live Price", f"{price:.4f}")
    c2.markdown(f"### Signal: <span style='color:{color}'>{arrow} {signal}</span>", unsafe_allow_html=True)
    c3.metric("RSI Strength", f"{rsi:.1f}")

    # Plotly Chart
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)

    # 5. GEMINI INSIGHT
    with st.container():
        st.subheader("🤖 Gemini AI Verdict")
        prompt = f"Data: {ticker} at {price}, RSI {rsi}. Signal is {signal}. Give a 1-sentence pro trader tip."
        response = model.generate_content(prompt)
        st.info(response.text)