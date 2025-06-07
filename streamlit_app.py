import os
import time
from datetime import datetime
import smtplib
from email.message import EmailMessage
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from apscheduler.schedulers.background import BackgroundScheduler
from fyers_bot import run_trading_bot, get_fyers_positions, get_fyers_funds
from fyers_apiv3 import fyersModel
from googlesearch import search

# Load credentials
APP_ID = st.secrets["FYERS"]["FYERS_APP_ID"]
ACCESS_TOKEN = st.secrets["FYERS"]["ACCESS_TOKEN"]

fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=f"{APP_ID}:{ACCESS_TOKEN}",
    log_path="logs/"
)

# Load Nifty 500 list
try:
    nifty_df = pd.read_csv("data/nifty500list.csv")
    STOCK_LIST = [f"{symbol}.NS" for symbol in nifty_df["Symbol"].dropna()]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

# Function to fetch relevant news sentiment
def news_sentiment_score(symbol):
    query = f"{symbol} stock news site:moneycontrol.com OR site:economictimes.indiatimes.com"
    results = list(search(query, num_results=5))
    return len(results)

# Select top 5 stocks based on news hits
def select_stocks_by_news():
    scores = []
    for sym in STOCK_LIST[:50]:  # Limit to top 50 for speed
        count = news_sentiment_score(sym.replace(".NS", ""))
        scores.append((sym, count))
    top = sorted(scores, key=lambda x: x[1], reverse=True)[:5]
    return [s[0] for s in top]

# Setup logs
os.makedirs("logs", exist_ok=True)

st.title("📊 Smart AI Trading Dashboard (Live Fyers Mode)")

# Trading mode
mode = st.radio("Select Trading Mode:", ["Simulation", "Live Trading"], index=0)
live_mode = mode == "Live Trading"

# User inputs
capital = st.number_input("Capital per trade (₹)", value=1000)
tp = st.slider("Take Profit %", 1, 10, value=2)
sl = st.slider("Stop Loss %", 1, 10, value=1)

# Recommended Stocks
recommended = select_stocks_by_news()
symbol = st.selectbox("📌 Choose Stock (from Nifty 500 with news buzz)", recommended)

# Load data
data = yf.download(symbol, period="3mo", interval="1d")
data['Signal'] = ["HOLD"] * len(data)
data.loc[data.index[-1], 'Signal'] = "BUY"

st.write("## Signal:", data['Signal'].iloc[-1])

fig = go.Figure()
fig.add_candlestick(x=data.index, open=data['Open'], high=data['High'],
                    low=data['Low'], close=data['Close'])
last_price = data['Close'].iloc[-1]
if data['Signal'].iloc[-1] == "BUY":
    fig.add_trace(go.Scatter(x=[data.index[-1]], y=[last_price], mode="markers",
                             marker=dict(color="green", size=12), name="BUY"))
st.plotly_chart(fig)

if st.button("Run AI Trade Now"):
    signal_df = pd.DataFrame([{"symbol": symbol, "signal": data['Signal'].iloc[-1]}])
    run_trading_bot(signal_df, live=live_mode, capital_per_trade=capital, tp_percent=tp, sl_percent=sl)
    st.success("✅ Trade processed in " + ("Live" if live_mode else "Simulation") + " mode!")

# Current Positions
st.header("📦 Portfolio (Fyers)")
positions = get_fyers_positions()
if positions:
    df_positions = pd.DataFrame(positions)
    df_positions["PnL_₹"] = df_positions["netQty"] * (df_positions["ltp"] - df_positions["avgPrice"])
    st.dataframe(df_positions[["symbol", "netQty", "avgPrice", "ltp", "PnL_₹"]])
else:
    st.info("No open positions.")

# Available Funds
st.header("💰 Funds Available (Fyers)")
funds = get_fyers_funds()
if funds:
    df_funds = pd.DataFrame(funds)
    st.dataframe(df_funds[["title", "equityAmount", "collateralAmount", "net"]])
else:
    st.info("Could not fetch funds.")

# Email Summary
def send_trade_summary_email():
    if os.path.exists("trade_log.csv"):
        try:
            df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.dropna(subset=["timestamp"])
            today = pd.Timestamp.now().normalize()
            daily = df[df["timestamp"].dt.normalize() == today]
            body = daily.to_string(index=False) if not daily.empty else "No trades executed today."
        except Exception as e:
            body = f"Error reading trade log: {e}"
    else:
        body = "Trade log not found."

    msg = EmailMessage()
    msg['Subject'] = '📈 Daily AI Trade Summary'
    msg['From'] = st.secrets["EMAIL"]["EMAIL_ADDRESS"]
    msg['To'] = st.secrets["EMAIL"]["EMAIL_ADDRESS"]
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(st.secrets["EMAIL"]["EMAIL_ADDRESS"], st.secrets["EMAIL"]["EMAIL_PASSWORD"])
            smtp.send_message(msg)
        print("✅ Email sent.")
    except Exception as e:
        print("❌ Email error:", e)

if "scheduler_started" not in st.session_state:
    scheduler = BackgroundScheduler(timezone='Asia/Kolkata')
    scheduler.add_job(send_trade_summary_email, "cron", hour=16, minute=30)
    scheduler.start()
    st.session_state.scheduler_started = True
    st.toast("📧 Email scheduled at 4:30 PM IST")

if st.button("Send Daily Trade Summary Now"):
    send_trade_summary_email()
    st.success("✅ Summary email sent.")
