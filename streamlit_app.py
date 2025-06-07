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
from fyers_bot import run_trading_bot

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

# Stock selection
stocks = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]
symbol = st.selectbox("Choose Stock:", stocks)

# Load data and generate dummy signal
data = yf.download(symbol, period="3mo", interval="1d")
data['Signal'] = ["HOLD"] * len(data)
data['Signal'].iloc[-1] = "BUY"  # Dummy signal for testing

# Show Signal
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

# Run trade
if st.button("Run AI Trade Now"):
    signal_df = pd.DataFrame([{"symbol": symbol, "signal": data['Signal'].iloc[-1]}])
    run_trading_bot(signal_df, live=live_mode, capital_per_trade=capital, tp_percent=tp, sl_percent=sl)
    st.success("Trade processed in " + ("Live" if live_mode else "Simulation") + " mode!")

# Email summary sender
def send_trade_summary_email():
    if os.path.exists("trade_log.csv"):
        df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action"])
        today = datetime.now().strftime("%Y-%m-%d")
        daily = df[df["timestamp"].str.contains(today)]
        body = daily.to_string(index=False) if not daily.empty else "No trades executed today."
    else:
        body = "Trade log file not found."

    msg = EmailMessage()
    msg['Subject'] = '📈 Daily Trade Summary - Smart AI Bot'
    msg['From'] = st.secrets["EMAIL"]["EMAIL_ADDRESS"]
    msg['To'] = st.secrets["EMAIL"]["EMAIL_ADDRESS"]
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(st.secrets["EMAIL"]["EMAIL_ADDRESS"], st.secrets["EMAIL"]["EMAIL_PASSWORD"])
            smtp.send_message(msg)
            print("✅ Daily trade summary email sent.")
    except Exception as e:
        print("❌ Email send failed:", e)

# Test manual summary send
if st.button("Send Daily Trade Summary Now"):
    send_trade_summary_email()
    st.success("Daily trade summary email sent.")

# Scheduler setup (runs only once)
if "scheduler_started" not in st.session_state:
    scheduler = BackgroundScheduler(timezone='Asia/Kolkata')
    scheduler.add_job(send_trade_summary_email, "cron", hour=16, minute=30)
    scheduler.start()
    st.session_state.scheduler_started = True
