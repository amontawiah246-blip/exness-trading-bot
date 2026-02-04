import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import json

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="Exness AI Bot", layout="wide")
st_autorefresh(interval=60000, key="bot_refresh") # Refresh every 60 seconds

# --- 2. API SETUP ---
# Make sure your API key is in Streamlit Secrets or replace 'YOUR_KEY_HERE'
API_KEY = st.secrets.get("GEMINI_API_KEY", "YOUR_KEY_HERE")
genai.configure(api_key=API_KEY)

# Initialize Session State for the signal so it persists during refreshes
if "ai_signal" not in st.session_state:
    st.session_state.ai_signal = None

# --- 3. HELPER FUNCTIONS ---
def get_ai_signal(ticker, price, rsi, adx):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        prompt = f"""
        Act as a professional forex scalper.
        Ticker: {ticker}
        Current Price: {price:.5f}
        RSI: {rsi:.2f}
        ADX: {adx:.2f}
        
        Provide a trade signal in JSON format only:
        {{ "signal": "BUY/SELL/WAIT", "confidence": 0-100, "reason": "short explanation" }}
        """
        response = model.generate_content(prompt)
        # Clean potential markdown from response
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        return {"signal": "ERROR", "confidence": 0, "reason": str(e)}

# --- 4. SIDEBAR ---
st.sidebar.header("🕹️ Control Panel")
ticker = st.sidebar.selectbox("Market", ["EURUSD=X", "GBPUSD=X", "BTC-USD", "USDJPY=X"])
timeframe = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m"], index=0)

# --- 5. DATA FETCHING ---
df = yf.download(ticker, period="1d", interval=timeframe)

if not df.empty:
    # Flatten multi-index columns if they exist
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Add Indicators
    df['RSI'] = ta.rsi(df['Close'], length=14)
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx_df], axis=1).dropna()
    
    last_row = df.iloc[-1]

    # --- 6. UI DASHBOARD ---
    st.title(f"📊 {ticker} Live Scalper")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Price", f"{last_row['Close']:.5f}")
    m2.metric("RSI", f"{last_row['RSI']:.1f}")
    m3.metric("Trend (ADX)", f"{last_row['ADX_14']:.1f}")

    # --- 7. THE CORRECTED CHART ---
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close']
    )])

    # FIX: Use 'template="plotly_dark"' instead of 'darkmode=True'
    fig.update_layout(
        template="plotly_dark",
        height=450,
        margin=dict(l=10, r=10, b=10, t=10),
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 8. THE SIGNAL BUTTON ---
    st.write("---")
    if st.button("🎯 GET AI SIGNAL NOW", use_container_width=True, type="primary"):
        with st.spinner("Analyzing market patterns..."):
            st.session_state.ai_signal = get_ai_signal(
                ticker, last_row['Close'], last_row['RSI'], last_row['ADX_14']
            )

    # Display results if they exist
    if st.session_state.ai_signal:
        res = st.session_state.ai_signal
        color = "green" if res['signal'] == "BUY" else "red" if res['signal'] == "SELL" else "orange"
        
        st.markdown(f"""
            <div style="border: 2px solid {color}; padding: 15px; border-radius: 10px; background-color: rgba(0,0,0,0.2);">
                <h3 style="color:{color}; margin-top:0;">{res['signal']} Signal ({res['confidence']}%)</h3>
                <p><strong>Reasoning:</strong> {res['reason']}</p>
            </div>
        """, unsafe_allow_html=True)
else:
    st.error("Connection error. Could not fetch market data.")
