import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import streamlit as st
import os
import time
import requests
from fyers_apiv3 import fyersModel
import schedule
import threading
import matplotlib.pyplot as plt
import yfinance as yf

# ✅ Ensure logs folder exists
os.makedirs("logs", exist_ok=True)

# Load credentials securely from Streamlit secrets
APP_ID = st.secrets["FYERS"]["FYERS_APP_ID"]
ACCESS_TOKEN = st.secrets["FYERS"]["ACCESS_TOKEN"]
TELEGRAM_TOKEN = st.secrets["ALERTS"]["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["ALERTS"]["TELEGRAM_CHAT_ID"]
EMAIL_FROM = st.secrets["EMAIL"]["EMAIL_FROM"]
EMAIL_PASS = st.secrets["EMAIL"]["EMAIL_PASSWORD"]
EMAIL_TO = st.secrets["EMAIL"]["EMAIL_TO"]

# Initialize Fyers model
fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=f"{APP_ID}:{ACCESS_TOKEN}",
    log_path="logs/"
)

# Load stock list from repo-local Nifty 500 file
STOCK_LIST = []
try:
    df_stocks = pd.read_csv("data/nifty500list.csv")
    STOCK_LIST = [f"{s.strip()}.NS" for s in df_stocks["Symbol"] if isinstance(s, str)]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

# Get live market price
@st.cache_data(ttl=60)
def get_live_price(symbol):
    try:
        headers = {"Authorization": f"Bearer {APP_ID}:{ACCESS_TOKEN}"}
        response = requests.get("https://api.fyers.in/data-rest/v2/quotes", params={"symbols": symbol}, headers=headers)
        return response.json()['d'][0]['v']['lp']
    except:
        return 0

# Place order
def place_order(symbol, side, qty):
    try:
        order = {
            "symbol": symbol, "qty": qty, "type": 2,
            "side": 1 if side == "BUY" else -1,
            "productType": "INTRADAY", "limitPrice": 0,
            "stopPrice": 0, "validity": "DAY",
            "disclosedQty": 0, "offlineOrder": False,
            "orderType": 1
        }
        return fyers.place_order(order)
    except Exception as e:
        print("[ORDER FAILED]", symbol, side, qty, e)
        return {}

# Check available funds
def get_funds():
    try:
        return fyers.funds().get("fund_limit", [])
    except:
        return []

# Log trade
def log_trade(symbol, action, qty, entry, tp, sl):
    with open("trade_log.csv", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{symbol},{action},{qty},{entry},{tp},{sl}\n")

# Telegram alert
def send_telegram_alert(symbol, action, price, tp, sl):
    try:
        msg = f"🚨 {action} {symbol}\nPrice: {price}, TP: {tp}, SL: {sl}"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram error:", e)

# Email report
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
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(f"<html><body><pre>{body}</pre></body></html>", "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(EMAIL_FROM, EMAIL_PASS)
            s.send_message(msg)
    except Exception as e:
        print("Email send failed:", e)

# Analyze a stock and return BUY/HOLD
def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="15d", interval="1h")
        if len(df) < 30: return "HOLD"
        df["EMA20"] = df["Close"].ewm(span=20).mean()
        df["EMA50"] = df["Close"].ewm(span=50).mean()
        df["Signal"] = ["BUY" if df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1] else "HOLD"]
        return df["Signal"].iloc[-1]
    except:
        return "HOLD"

# Main trading bot
def run_trading_bot(live=True, capital_per_trade=1000, tp_percent=2, sl_percent=1):
    try:
        funds = get_funds()
        total_equity = next((f["equityAmount"] for f in funds if f.get("title") == "Total Cash"), 0)
    except:
        total_equity = 0

    for symbol in STOCK_LIST:
        signal = analyze_stock(symbol)
        if signal != "BUY":
            continue

        price = get_live_price(symbol)
        if price <= 0:
            continue
        qty = max(int(capital_per_trade // price), 1)
        cost = qty * price

        if live and total_equity < cost:
            print(f"❌ Skipping {symbol} due to insufficient funds.")
            continue

        tp_price = round(price * (1 + tp_percent / 100), 2)
        sl_price = round(price * (1 - sl_percent / 100), 2)

        if live:
            place_order(symbol, "BUY", qty)

        log_trade(symbol, "BUY", qty, price, tp_price, sl_price)
        send_telegram_alert(symbol, "BUY", price, tp_price, sl_price)

# Plot profit/loss history
def plot_trade_history():
    if not os.path.exists("trade_log.csv"):
        return
    df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["PnL"] = df.apply(
        lambda x: (x["tp"] - x["entry"]) * x["qty"] if x["action"] == "BUY"
        else (x["entry"] - x["tp"]) * x["qty"], axis=1)
    df = df.sort_values("timestamp")
    df["CumulativePnL"] = df["PnL"].cumsum()
    st.line_chart(df.set_index("timestamp")["CumulativePnL"])

# Auto start scheduler
def start_scheduler():
    schedule.every().day.at("09:15").do(lambda: run_trading_bot(live=True))
    schedule.every().day.at("16:30").do(send_trade_summary_email)
    threading.Thread(target=lambda: [schedule.run_pending() or time.sleep(60)], daemon=True).start()

# Streamlit dashboard
def main_dashboard():
    st.title("🚀 Smart AI Trading Bot")
    st.write(f"📈 Loaded {len(STOCK_LIST)} stocks from Nifty 500.")
    st.info("Bot will auto-start daily at 9:15 AM IST. Check logs for actions.")
    plot_trade_history()

start_scheduler()
main_dashboard()
