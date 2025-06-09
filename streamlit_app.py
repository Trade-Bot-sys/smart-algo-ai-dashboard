import os
import json
import requests
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

# ✅ Set Streamlit config
st.set_page_config(layout="wide", page_title="Smart AI Trading Dashboard")
st.title("📈 Smart AI Trading Dashboard")

# ✅ Load secrets
EMAIL = st.secrets["EMAIL"]["EMAIL_ADDRESS"]
EMAIL_PASS = st.secrets["EMAIL"]["EMAIL_PASSWORD"]
TELEGRAM_TOKEN = st.secrets["ALERTS"]["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["ALERTS"]["TELEGRAM_CHAT_ID"]

# ✅ Load Angel One access token
with open("access_token.json") as f:
    token_data = json.load(f)
client_id = token_data["client_id"]
access_token = token_data["access_token"]

# ✅ Stock list
try:
    df_stocks = pd.read_csv("data/nifty500list.csv")
    STOCK_LIST = [f"{s.strip()}.NS" for s in df_stocks["Symbol"] if isinstance(s, str)]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

# ✅ Get live price
@st.cache_data(ttl=60)
def get_live_price(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m")
        return df["Close"].iloc[-1]
    except:
        return 0

# ✅ Place order (Dummy logic – Replace with Angel One API)
def place_order(symbol, side, qty):
    print(f"✅ [SIMULATED] Placing {side} order for {symbol} - Qty: {qty}")
    return {"status": True}

# ✅ Telegram alert
def send_telegram_alert(symbol, action, price, tp, sl):
    try:
        msg = f"🚨 {action} {symbol}\nPrice: {price}, TP: {tp}, SL: {sl}"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram error:", e)

# ✅ Send summary email
def send_trade_summary_email():
    if not os.path.exists("trade_log.csv"):
        return
    try:
        df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])
        body = df[df["timestamp"].dt.date == pd.Timestamp.now().date()].to_string(index=False)
    except Exception as e:
        body = f"Error parsing trade log: {e}"

    msg = MIMEMultipart()
    msg["Subject"] = "📈 Daily AI Trade Summary"
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg.attach(MIMEText(f"<html><body><pre>{body}</pre></body></html>", "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(EMAIL, EMAIL_PASS)
            s.send_message(msg)
    except Exception as e:
        print("Email failed:", e)

# ✅ Signal logic
@st.cache_data(ttl=600)
def get_signal(symbol):
    try:
        df = yf.download(symbol, period="15d", interval="1h")
        if len(df) < 30:
            return "HOLD"
        df["EMA20"] = df["Close"].ewm(span=20).mean()
        df["EMA50"] = df["Close"].ewm(span=50).mean()
        df["VolumeAvg"] = df["Volume"].rolling(window=20).mean()
        df["MACD"] = df["Close"].ewm(span=12).mean() - df["Close"].ewm(span=26).mean()

        ema = df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1]
        volume = df["Volume"].iloc[-1] > 1.2 * df["VolumeAvg"].iloc[-1]
        macd = df["MACD"].iloc[-1] > 0

        return "BUY" if ema and volume and macd else "HOLD"
    except:
        return "HOLD"

# ✅ Run bot
def run_trading_bot(live=True, capital_per_trade=1000, tp_percent=2, sl_percent=1):
    for symbol in STOCK_LIST[:10]:
        signal = get_signal(symbol)
        if signal != "BUY":
            continue

        price = get_live_price(symbol)
        if price <= 0:
            continue

        qty = max(int(capital_per_trade // price), 1)
        tp_price = round(price * (1 + tp_percent / 100), 2)
        sl_price = round(price * (1 - sl_percent / 100), 2)

        if live:
            place_order(symbol, "BUY", qty)

        with open("trade_log.csv", "a") as f:
            f.write(f"{datetime.now()},{symbol},BUY,{qty},{price},{tp_price},{sl_price}\n")

        send_telegram_alert(symbol, "BUY", price, tp_price, sl_price)

# ✅ Scheduler
if "scheduler_started" not in st.session_state:
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(lambda: run_trading_bot(live=True), "cron", hour=9, minute=15)
    scheduler.add_job(send_trade_summary_email, "cron", hour=16, minute=30)
    scheduler.start()
    st.session_state.scheduler_started = True

# ✅ UI Inputs
capital = st.number_input("Capital per Trade (₹)", value=1000)
tp = st.slider("Take Profit %", 1, 10, 2)
sl = st.slider("Stop Loss %", 1, 10, 1)

top_stock = STOCK_LIST[0]
signal = get_signal(top_stock)
st.subheader(f"🔍 Signal for {top_stock}: {signal}")

data = yf.download(top_stock, period="3mo", interval="1d")
fig = go.Figure()
fig.add_candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])
if signal == "BUY":
    fig.add_trace(go.Scatter(x=[data.index[-1]], y=[data['Close'].iloc[-1]], mode="markers", marker=dict(color="green", size=10)))
st.plotly_chart(fig)

# ✅ Trade history chart
if os.path.exists("trade_log.csv"):
    df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["PnL"] = (df["tp"] - df["entry"]) * df["qty"]
    df["CumulativePnL"] = df["PnL"].cumsum()
    st.header("📊 Trade History PnL")
    st.line_chart(df.set_index("timestamp")["CumulativePnL"])

# ✅ Manual trigger
if st.button("📤 Send Summary Email Now"):
    send_trade_summary_email()
    st.success("📧 Sent!")

if st.button("🔔 Test Telegram"):
    send_telegram_alert("DEMO", "BUY", 100, 102, 98)
    st.success("Telegram alert sent!")
