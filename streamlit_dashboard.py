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
st.title("📈 Smart AI Trading Dashboard - Angel One")

# ✅ Load secrets
EMAIL = st.secrets["EMAIL"]["EMAIL_ADDRESS"]
EMAIL_PASS = st.secrets["EMAIL"]["EMAIL_PASSWORD"]
TELEGRAM_TOKEN = st.secrets["ALERTS"]["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["ALERTS"]["TELEGRAM_CHAT_ID"]

# ✅ Load Angel One access token
with open("access_token.json") as f:
    token_data = json.load(f)
API_KEY = token_data["api_key"]
CLIENT_ID = token_data["client_id"]
JWT_TOKEN = token_data["access_token"]

# ✅ Angel headers
HEADERS = {
    "Authorization": f"Bearer {JWT_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-UserType": "USER",
    "X-SourceID": "WEB",
    "X-ClientLocalIP": "127.0.0.1",
    "X-ClientPublicIP": "127.0.0.1",
    "X-MACAddress": "AA:BB:CC:DD:EE:FF",
    "X-PrivateKey": API_KEY
}

# ✅ Load stock list
try:
    df_stocks = pd.read_csv("data/nifty500list.csv")
    STOCK_LIST = [f"{s.strip()}.NS" for s in df_stocks["Symbol"] if isinstance(s, str)]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

@st.cache_data(ttl=60)
def get_live_price(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m")
        return df["Close"].iloc[-1]
    except:
        return 0

def place_order(symbol, side, qty):
    try:
        sym = symbol.replace(".NS", "-EQ")
        order = {
            "variety": "NORMAL",
            "tradingsymbol": sym,
            "symboltoken": "3045",  # Replace with actual token mapping
            "transactiontype": side,
            "exchange": "NSE",
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "price": "0",
            "squareoff": "0",
            "stoploss": "0",
            "quantity": str(qty)
        }
        r = requests.post("https://apiconnect.angelbroking.com/rest/secure/angelbroking/order/v1/placeOrder",
                          headers=HEADERS, json=order)
        return r.json()
    except Exception as e:
        print("Order Error:", e)
        return {}

def send_telegram_alert(symbol, action, price, tp, sl):
    try:
        msg = f"🚨 {action} {symbol}\nPrice: ₹{price}, TP: ₹{tp}, SL: ₹{sl}"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram Error:", e)

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
    msg["Subject"] = "📈 Daily Trade Summary"
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg.attach(MIMEText(f"<html><body><pre>{body}</pre></body></html>", "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(EMAIL, EMAIL_PASS)
            s.send_message(msg)
    except Exception as e:
        print("Email Error:", e)

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

        if (df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1] and
            df["Volume"].iloc[-1] > 1.2 * df["VolumeAvg"].iloc[-1] and
            df["MACD"].iloc[-1] > 0):
            return "BUY"
        return "HOLD"
    except:
        return "HOLD"

def run_trading_bot(live=True, capital_per_trade=1000, tp_percent=2, sl_percent=1):
    for symbol in STOCK_LIST[:10]:
        signal = get_signal(symbol)
        if signal != "BUY":
            continue
        price = get_live_price(symbol)
        if price <= 0:
            continue
        qty = max(int(capital_per_trade // price), 1)
        tp = round(price * (1 + tp_percent / 100), 2)
        sl = round(price * (1 - sl_percent / 100), 2)
        if live:
            place_order(symbol, "BUY", qty)
        with open("trade_log.csv", "a") as f:
            f.write(f"{datetime.now()},{symbol},BUY,{qty},{price},{tp},{sl}\n")
        send_telegram_alert(symbol, "BUY", price, tp, sl)

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

symbol = STOCK_LIST[0]
signal = get_signal(symbol)
st.subheader(f"🔍 Signal for {symbol}: {signal}")
data = yf.download(symbol, period="3mo", interval="1d")
fig = go.Figure()
fig.add_candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])
if signal == "BUY":
    fig.add_trace(go.Scatter(x=[data.index[-1]], y=[data['Close'].iloc[-1]], mode="markers", marker=dict(color="green", size=10)))
st.plotly_chart(fig)

# ✅ Trade log chart
if os.path.exists("trade_log.csv"):
    df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["PnL"] = (df["tp"] - df["entry"]) * df["qty"]
    df["CumulativePnL"] = df["PnL"].cumsum()
    st.header("📊 Trade History PnL")
    st.line_chart(df.set_index("timestamp")["CumulativePnL"])

# ✅ Manual triggers
if st.button("📤 Send Summary Email Now"):
    send_trade_summary_email()
    st.success("📧 Email sent!")

if st.button("🔔 Test Telegram"):
    send_telegram_alert("DEMO", "BUY", 100, 102, 98)
    st.success("Telegram alert sent!")

