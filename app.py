import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime

# --- SET PAGE CONFIG ---
st.set_page_config(page_title="Exness AI Dashboard", layout="wide")

# --- SECURE API SETUP ---
# Make sure "GEMINI_API_KEY" is added to your Streamlit Cloud Secrets!
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Using 'gemini-1.5-flash-latest' to avoid 404 errors
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    st.error("⚠️ Gemini API Key not found in Secrets. Please add it to Streamlit Settings.")

def get_analysis(ticker):
    # 1. Fetch Data
    data = yf.download(ticker, period="1d", interval="15m")
    
    # 2. FIX: MultiIndex Column Error
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    if data.empty:
        return None, None, None, None, None, None

    # 3. Calculate Indicators
    data['RSI'] = ta.rsi(data['Close'], length=14)
    data['EMA_20'] = ta.ema(data['Close'], length=20)
    
    last_row = data.iloc[-1]
    price = round(last_row['Close'], 5)
    rsi = round(last_row['RSI'], 2)
    
    # 4. Signal Logic
    if rsi < 35:
        signal, color, arrow = "BUY", "#00FF00", "▲"
    elif rsi > 65:
        signal, color, arrow = "SELL", "#FF0000", "▼"
    else:
        signal, color, arrow = "NEUTRAL", "#AAAAAA", ""
        
    return data, price, rsi, signal, color, arrow

# --- UI DESIGN ---
st.title("🤖 Exness AI Trading Dashboard")
ticker = st.text_input("Enter Ticker (e.g., EURUSD=X, BTC-USD, AAPL)", "EURUSD=X")

if st.button("GET LIVE SIGNAL"):
    df, price, rsi, signal, color, arrow = get_analysis(ticker)
    
    if df is not None:
        # Metrics Row
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Price", price)
        col2.metric("RSI (14)", rsi)
        col3.markdown(f"### Signal: <span style='color:{color}'>{signal} {arrow}</span>", unsafe_allow_html=True)
        
        # Plotly Candlestick Chart
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="Price"
        )])
        
        # Add the Signal Arrow to the chart
        if arrow:
            fig.add_annotation(
                x=df.index[-1], y=df['Close'].iloc[-1],
                text=f"{signal} {arrow}", showarrow=True,
                arrowhead=2, bgcolor=color, font=dict(color="white")
            )
            
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # AI Insight Section
        st.subheader("💡 AI Market Insight")
        with st.spinner("Analyzing market structure..."):
            try:
                prompt = f"Act as a professional forex trader. Ticker: {ticker}. Price: {price}. RSI: {rsi}. Signal: {signal}. Provide a 2-sentence strategy."
                response = model.generate_content(prompt)
                st.write(response.text)
            except:
                st.write("AI is currently unavailable, but your technical indicators are live!")
    else:
        st.error("Ticker not found. Please check the symbol and try again.")
