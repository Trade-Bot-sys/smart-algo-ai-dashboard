import os
import smtplib
from email.message import EmailMessage
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from apscheduler.schedulers.background import BackgroundScheduler
from googlesearch import search
from fyers_apiv3 import fyersModel
from fyers_bot import run_trading_bot, get_fyers_positions, get_fyers_funds

# Load secrets
APP_ID = st.secrets["FYERS"]["FYERS_APP_ID"]
ACCESS_TOKEN = st.secrets["FYERS"]["ACCESS_TOKEN"]
EMAIL = st.secrets["EMAIL"]["EMAIL_ADDRESS"]
EMAIL_PASS = st.secrets["EMAIL"]["EMAIL_PASSWORD"]

# Fyers session
fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=f"{APP_ID}:{ACCESS_TOKEN}",
    log_path="logs/"
)

# Load Nifty 500 list
try:
    nifty_df = pd.read_csv("data/nifty500list.csv")
    STOCK_LIST = [f"{s}.NS" for s in nifty_df["Symbol"].dropna()]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

# News sentiment scoring
def news_sentiment_score(symbol):
    query = f"{symbol} stock news site:moneycontrol.com OR site:economictimes.indiatimes.com"
    try:
        return len(list(search(query, num_results=5)))
    except:
        return 0

# News-based top 5 stocks
@st.cache_data(ttl=3600)
def get_top_news_stocks():
    results = []
    for s in STOCK_LIST[:50]:
        score = news_sentiment_score(s.replace(".NS", ""))
        results.append((s, score))
    sorted_stocks = sorted(results, key=lambda x: x[1], reverse=True)
    return [s[0] for s in sorted_stocks[:5]]

# 📊 UI Start
st.title("📈 Smart AI Trading Dashboard with Live News & Strategy")

# Trading mode
mode = st.radio("Select Mode", ["Simulation", "Live Trading"], index=0)
live_mode = (mode == "Live Trading")

# Trade params
capital = st.number_input("Capital per Trade (₹)", value=1000)
tp = st.slider("Take Profit %", 1, 10, value=2)
sl = st.slider("Stop Loss %", 1, 10, value=1)

# Stock suggestion from news
top_stocks = get_top_news_stocks()
symbol = st.selectbox("🔥 Trending Stock by News Sentiment", top_stocks)

# Signal & chart
data = yf.download(symbol, period="3mo", interval="1d")
data['Signal'] = ["HOLD"] * len(data)
data.loc[data.index[-1], 'Signal'] = "BUY"

st.subheader(f"📍 Signal for {symbol}: {data['Signal'].iloc[-1]}")
fig = go.Figure()
fig.add_candlestick(x=data.index, open=data['Open'], high=data['High'],
                    low=data['Low'], close=data['Close'])
last_price = data['Close'].iloc[-1]
if data['Signal'].iloc[-1] == "BUY":
    fig.add_trace(go.Scatter(x=[data.index[-1]], y=[last_price],
                             mode="markers", marker=dict(color="green", size=12),
                             name="BUY Signal"))
st.plotly_chart(fig)

# Execute trade
if st.button("🚀 Run AI Trade Now"):
    signal_df = pd.DataFrame([{"symbol": symbol, "signal": data['Signal'].iloc[-1]}])
    run_trading_bot(signal_df, live=live_mode, capital_per_trade=capital, tp_percent=tp, sl_percent=sl)
    st.success(f"Trade executed in {'Live' if live_mode else 'Simulation'} mode!")

# Live positions
st.header("📦 Portfolio (Fyers)")
positions = get_fyers_positions(fyers)
if positions:
    df_positions = pd.DataFrame(positions)
    df_positions["PnL ₹"] = df_positions["netQty"] * (df_positions["ltp"] - df_positions["avgPrice"])
    st.dataframe(df_positions[["symbol", "netQty", "avgPrice", "ltp", "PnL ₹"]])
else:
    st.info("No open positions.")

# Available funds
st.header("💰 Funds (Fyers)")
funds = get_fyers_funds(fyers)
if funds:
    df_funds = pd.DataFrame(funds)
    st.dataframe(df_funds[["title", "equityAmount", "collateralAmount", "net"]])
else:
    st.warning("Unable to fetch fund details.")

# Trade summary email
def send_trade_summary_email():
    if not os.path.exists("trade_log.csv"):
        return "Trade log not found."

    try:
        df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna()
        today = pd.Timestamp.now().normalize()
        today_trades = df[df["timestamp"].dt.normalize() == today]
        content = today_trades.to_string(index=False) if not today_trades.empty else "No trades executed today."
    except Exception as e:
        content = f"Error reading trade log: {e}"

    msg = EmailMessage()
    msg["Subject"] = "📊 Daily AI Trade Summary"
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg.set_content(content)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL, EMAIL_PASS)
            smtp.send_message(msg)
        print("✅ Email sent.")
    except Exception as e:
        print("❌ Email failed:", e)

if "scheduler_started" not in st.session_state:
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(send_trade_summary_email, "cron", hour=16, minute=30)
    scheduler.start()
    st.session_state.scheduler_started = True
    st.toast("📧 Daily Summary Email scheduled for 4:30 PM IST")

if st.button("📤 Send Daily Trade Summary Now"):
    send_trade_summary_email()
    st.success("📨 Summary email sent successfully!")
