import os, json, time, requests, schedule, threading, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import pandas as pd
import yfinance as yf
import streamlit as st
import matplotlib.pyplot as plt

# ✅ Read from access_token.json
with open("access_token.json") as f:
    data = json.load(f)
API_KEY = data.get("api_key")
CLIENT_ID = data.get("client_id")
JWT_TOKEN = data.get("access_token")

# ✅ Streamlit Secrets
EMAIL_FROM = st.secrets["EMAIL"]["EMAIL_FROM"]
EMAIL_TO = st.secrets["EMAIL"]["EMAIL_TO"]
EMAIL_PASS = st.secrets["EMAIL"]["EMAIL_PASSWORD"]
TELEGRAM_TOKEN = st.secrets["ALERTS"]["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["ALERTS"]["TELEGRAM_CHAT_ID"]

os.makedirs("logs", exist_ok=True)

# ✅ Stock list
try:
    df_stocks = pd.read_csv("data/nifty500list.csv")
    STOCK_LIST = [f"{s.strip()}.NS" for s in df_stocks["Symbol"] if isinstance(s, str)]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

# ✅ Angel REST headers
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

def get_live_price(symbol):
    try:
        sym = symbol.replace(".NS", "-EQ")
        url = f"https://apiconnect.angelbroking.com/rest/secure/market/v1/quote/{sym}"
        r = requests.get(url, headers=HEADERS)
        return float(r.json()["data"]["ltp"])
    except:
        return 0

def place_order(symbol, side, qty):
    try:
        sym = symbol.replace(".NS", "-EQ")
        order = {
            "variety": "NORMAL",
            "tradingsymbol": sym,
            "symboltoken": "3045",  # NOTE: Replace with actual token per stock
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
        res = requests.post("https://apiconnect.angelbroking.com/rest/secure/angelbroking/order/v1/placeOrder",
                            headers=HEADERS, json=order)
        return res.json()
    except Exception as e:
        print(f"[ORDER ERROR] {symbol}: {e}")
        return {}

def log_trade(symbol, action, qty, entry, tp, sl):
    with open("trade_log.csv", "a") as f:
        f.write(f"{datetime.now()},{symbol},{action},{qty},{entry},{tp},{sl}\n")

def send_telegram_alert(symbol, action, price, tp, sl):
    try:
        msg = f"🚨 {action} {symbol}\nPrice: ₹{price}, TP: ₹{tp}, SL: ₹{sl}"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except:
        pass

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
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(f"<html><body><pre>{body}</pre></body></html>", "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(EMAIL_FROM, EMAIL_PASS)
            s.send_message(msg)
    except Exception as e:
        print("Email failed:", e)

def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="15d", interval="1h")
        if len(df) < 30: return "HOLD"
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
    for symbol in STOCK_LIST:
        signal = analyze_stock(symbol)
        if signal != "BUY":
            continue
        price = get_live_price(symbol)
        if price <= 0: continue
        qty = max(int(capital_per_trade // price), 1)
        tp_price = round(price * (1 + tp_percent / 100), 2)
        sl_price = round(price * (1 - sl_percent / 100), 2)
        if live:
            place_order(symbol, "BUY", qty)
        log_trade(symbol, "BUY", qty, price, tp_price, sl_price)
        send_telegram_alert(symbol, "BUY", price, tp_price, sl_price)

def plot_trade_history():
    if not os.path.exists("trade_log.csv"):
        st.info("No trade history.")
        return
    df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["PnL"] = (df["tp"] - df["entry"]) * df["qty"]
    df["CumulativePnL"] = df["PnL"].cumsum()
    st.subheader("📈 Cumulative PnL")
    st.line_chart(df.set_index("timestamp")["CumulativePnL"])

# ✅ Start Streamlit App
st.title("💹 Angel One Smart AI Trading Bot")

capital = st.number_input("Capital per trade (₹)", value=1000)
tp = st.slider("Take Profit %", 1, 10, 2)
sl = st.slider("Stop Loss %", 1, 10, 1)

if st.button("🚀 Run Trading Bot Now"):
    run_trading_bot(live=True, capital_per_trade=capital, tp_percent=tp, sl_percent=sl)
    st.success("Bot run completed.")

plot_trade_history()

if st.button("📤 Send Summary Email"):
    send_trade_summary_email()
    st.success("Sent email.")

if st.button("🔔 Send Test Alert"):
    send_telegram_alert("TEST", "BUY", 100, 102, 98)
    st.success("Telegram alert sent.")
