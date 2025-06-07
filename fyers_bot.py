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

# Load credentials securely from Streamlit secrets
APP_ID = st.secrets["FYERS"]["FYERS_APP_ID"]
APP_SECRET = st.secrets["FYERS"]["FYERS_APP_SECRET"]
REDIRECT_URI = st.secrets["FYERS"]["FYERS_REDIRECT_URI"]
ACCESS_TOKEN = st.secrets["FYERS"]["ACCESS_TOKEN"]
TELEGRAM_TOKEN = st.secrets["ALERTS"]["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["ALERTS"]["TELEGRAM_CHAT_ID"]

# Initialize Fyers model
fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=f"{APP_ID}:{ACCESS_TOKEN}",
    log_path="logs/"
)

# Get live market price
@st.cache_data(ttl=60)
def get_live_price(symbol):
    try:
        data = {"symbols": symbol}
        headers = {"Authorization": f"Bearer {APP_ID}:{ACCESS_TOKEN}"}
        response = requests.get("https://api.fyers.in/data-rest/v2/quotes", params=data, headers=headers)
        res_json = response.json()
        return res_json['d'][0]['v']['lp']  # Last traded price
    except Exception as e:
        print("Price fetch failed for", symbol, "Error:", e)
        return 0

# Place order using Fyers API
def place_order(symbol, side, qty):
    try:
        order = {
            "symbol": symbol,
            "qty": qty,
            "type": 2,
            "side": 1 if side == "BUY" else -1,
            "productType": "INTRADAY",
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
            "orderType": 1
        }
        response = fyers.place_order(order)
        print("[TRADE EXECUTED]", side, symbol, "| Qty:", qty, "| Response:", response)
        return response
    except Exception as e:
        print("[ORDER FAILED]", symbol, side, qty, "Error:", e)
        return {}

# Log executed trades
def log_trade(symbol, action, qty, entry_price, tp_price, sl_price):
    os.makedirs("logs", exist_ok=True)
    log_line = f"{time.strftime('%Y-%m-%d %H:%M:%S')},{symbol},{action},{qty},{entry_price},{tp_price},{sl_price}\n"
    with open("trade_log.csv", "a") as f:
        f.write(log_line)

# Main trading function
def run_trading_bot(signals_df, live=True, capital_per_trade=10000, tp_percent=2, sl_percent=1):
    for _, row in signals_df.iterrows():
        symbol = row['symbol']
        action = row['signal']
        if action in ["BUY", "SELL"]:
            price = get_live_price(symbol)
            if price <= 0:
                st.warning(f"Skipping {symbol} - failed to fetch price")
                continue

            qty = max(int(capital_per_trade // price), 1)
            tp_price = round(price * (1 + tp_percent / 100), 2) if action == "BUY" else round(price * (1 - tp_percent / 100), 2)
            sl_price = round(price * (1 - sl_percent / 100), 2) if action == "BUY" else round(price * (1 + sl_percent / 100), 2)

            if live:
                place_order(symbol, action, qty)

            log_trade(symbol, action, qty, price, tp_price, sl_price)
            send_telegram_alert(symbol, action, price, tp_price, sl_price)

# Get current positions
def get_fyers_positions():
    try:
        positions = fyers.positions()
        return positions.get("netPositions", [])
    except Exception as e:
        print("[ERROR] Failed to fetch positions:", e)
        return []

# Get available funds
def get_fyers_funds():
    try:
        funds = fyers.funds()
        return funds.get("fundLimit", {})
    except Exception as e:
        print("[ERROR] Failed to fetch funds:", e)
        return {}

# Send daily summary email
def send_trade_summary_email():
    email_from = st.secrets["EMAIL"]["EMAIL_FROM"]
    email_to = st.secrets["EMAIL"]["EMAIL_TO"]
    email_password = st.secrets["EMAIL"]["EMAIL_PASSWORD"]

    if not os.path.exists("trade_log.csv"):
        print("[EMAIL] No trade log file found.")
        return

    with open("trade_log.csv", "r") as f:
        trades = f.readlines()

    if not trades:
        print("[EMAIL] No trade entries to report.")
        return

    latest_trades = trades[-10:]
    summary_html = "<br>".join([f"<b>{line.strip()}</b>" for line in latest_trades])

    msg = MIMEMultipart()
    msg["Subject"] = "\U0001F4CA Daily AI Trade Summary"
    msg["From"] = email_from
    msg["To"] = email_to

    body = f"""
    <html>
    <body>
    <h2>\U0001F4C8 AI Trading Summary - {pd.Timestamp.now().strftime('%Y-%m-%d')}</h2>
    {summary_html}
    </body>
    </html>
    """
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email_from, email_password)
            server.send_message(msg)
        print("[EMAIL SENT] Daily trade summary email sent successfully.")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send summary email: {e}")

# Send Telegram alerts
def send_telegram_alert(symbol, action, price, tp, sl):
    try:
        msg = f"\U0001F6A8 {action} Alert for {symbol}\nPrice: {price}\nTP: {tp}, SL: {sl}"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        requests.post(url, data=payload)
    except Exception as e:
        print("[TELEGRAM ERROR]", e)

# Schedule daily job at 9:15 AM IST
def start_scheduler():
    schedule.every().day.at("09:15").do(lambda: run_trading_bot(pd.read_csv("signals.csv")))
    while True:
        schedule.run_pending()
        time.sleep(30)

# Start auto-run scheduler in background
def start_trading_bot():
    threading.Thread(target=start_scheduler, daemon=True).start()

# Profit/loss graph for trades
def plot_trade_history():
    if not os.path.exists("trade_log.csv"):
        st.info("No trade history found.")
        return
    df = pd.read_csv("trade_log.csv", header=None,
                     names=["Date", "Symbol", "Action", "Qty", "Entry", "TP", "SL"])
    df["PnL"] = df.apply(lambda x: (x["TP"] - x["Entry"]) * x["Qty"] if x["Action"] == "BUY" else (x["Entry"] - x["TP"]) * x["Qty"], axis=1)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")
    df["CumulativePnL"] = df["PnL"].cumsum()
    st.line_chart(df.set_index("Date")["CumulativePnL"])

# Launch dashboard
def main_dashboard():
    st.title("\U0001F680 Smart AI Trading Dashboard")
    plot_trade_history()

start_trading_bot()
main_dashboard()
