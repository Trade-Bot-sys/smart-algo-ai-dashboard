import os
import time
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from fyers_apiv3 import fyersModel
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from fyers_bot import run_trading_bot

# Setup log directory
os.makedirs("logs", exist_ok=True)

# Title and Trading Mode
st.title("📊 Smart AI Trading Dashboard (Live Fyers Mode)")
mode = st.radio("Select Trading Mode:", ["Simulation", "Live Trading"], index=0)
live_mode = mode == "Live Trading"

# Capital, TP, SL inputs
capital = st.number_input("Capital per trade (₹)", value=1000)
tp = st.slider("Take Profit %", 1, 10, value=2)
sl = st.slider("Stop Loss %", 1, 10, value=1)

# Stock selection
stocks = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]
symbol = st.selectbox("Choose Stock:", stocks)

# Fetch data
data = yf.download(symbol, period="3mo", interval="1d")
data['Signal'] = ["HOLD"] * len(data)
data['Signal'].iloc[-1] = "BUY"

# Show current signal
st.write("## Signal: ", data['Signal'].iloc[-1])

# Plot chart
fig = go.Figure()
fig.add_candlestick(x=data.index, open=data['Open'], high=data['High'],
                    low=data['Low'], close=data['Close'])
last_price = data['Close'].iloc[-1]
if data['Signal'].iloc[-1] == "BUY":
    fig.add_trace(go.Scatter(x=[data.index[-1]], y=[last_price], mode="markers",
                             marker=dict(color="green", size=12), name="BUY"))
elif data['Signal'].iloc[-1] == "SELL":
    fig.add_trace(go.Scatter(x=[data.index[-1]], y=[last_price], mode="markers",
                             marker=dict(color="red", size=12), name="SELL"))
st.plotly_chart(fig)

# Run Trade Button
if st.button("Run AI Trade Now"):
    signal_df = pd.DataFrame([{"symbol": symbol, "signal": data['Signal'].iloc[-1]}])
    run_trading_bot(signal_df, live=live_mode, capital_per_trade=capital, tp_percent=tp, sl_percent=sl)
    st.success("Trade processed in " + ("Live" if live_mode else "Simulation") + " mode!")

# Scheduler for summary email
scheduler = BackgroundScheduler(timezone='Asia/Kolkata')

def send_summary():
    if os.path.exists("trade_log.csv"):
        df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action"])
        today = datetime.now().strftime("%Y-%m-%d")
        daily = df[df["timestamp"].str.contains(today)]
        body = daily.to_string(index=False) if not daily.empty else "No trades executed today."
    else:
        body = "Trade log file not found."

    message = Mail(
        from_email='tradingstrategieswithram@gmail.com',
        to_emails='tradingstrategieswithram@gmail.com',
        subject='Daily Trade Summary - Smart AI Bot',
        plain_text_content=body
    )
    try:
        sg = SendGridAPIClient(st.secrets["SENDGRID_API_KEY"])
        sg.send(message)
        print("✅ Daily trade summary sent.")
    except Exception as e:
        print("❌ Failed to send summary:", e)

scheduler.add_job(send_summary, "cron", hour=16, minute=30)
scheduler.start()
