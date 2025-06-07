import os, time, threading, requests, schedule, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pandas as pd
import yfinance as yf
import streamlit as st
import matplotlib.pyplot as plt
from fyers_apiv3 import fyersModel

# ✅ Setup logs
os.makedirs("logs", exist_ok=True)

# ✅ Load credentials from Streamlit secrets
APP_ID = st.secrets["FYERS"]["FYERS_APP_ID"]
ACCESS_TOKEN = st.secrets["FYERS"]["ACCESS_TOKEN"]
EMAIL_FROM = st.secrets["EMAIL"]["EMAIL_FROM"]
EMAIL_TO = st.secrets["EMAIL"]["EMAIL_TO"]
EMAIL_PASS = st.secrets["EMAIL"]["EMAIL_PASSWORD"]
TELEGRAM_TOKEN = st.secrets["ALERTS"]["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["ALERTS"]["TELEGRAM_CHAT_ID"]

# ✅ Fyers login
fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=f"{APP_ID}:{ACCESS_TOKEN}",
    log_path="logs/"
)

# ✅ Load stock list
try:
    df_stocks = pd.read_csv("data/nifty500list.csv")
    STOCK_LIST = [f"{s.strip()}.NS" for s in df_stocks["Symbol"] if isinstance(s, str)]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

@st.cache_data(ttl=60)
def get_live_price(symbol):
    try:
        headers = {"Authorization": f"Bearer {APP_ID}:{ACCESS_TOKEN}"}
        r = requests.get("https://api.fyers.in/data-rest/v2/quotes", params={"symbols": symbol}, headers=headers)
        return r.json()['d'][0]['v']['lp']
    except:
        return 0

def place_order(symbol, side, qty):
    try:
        return fyers.place_order({
            "symbol": symbol, "qty": qty, "type": 2,
            "side": 1 if side == "BUY" else -1,
            "productType": "INTRADAY", "limitPrice": 0,
            "stopPrice": 0, "validity": "DAY",
            "disclosedQty": 0, "offlineOrder": False,
            "orderType": 1
        })
    except Exception as e:
        print(f"[ORDER FAIL] {symbol}: {e}")
        return {}

def get_fyers_positions():
    try:
        positions = fyers.positions()
        return positions.get("netPositions", [])
    except Exception as e:
        print("[ERROR] Failed to fetch positions:", e)
        return []

def get_fyers_funds():
    try:
        return fyers.funds().get("fundLimit", [])
    except Exception as e:
        print("[FUNDS ERROR]", e)
        return []

def log_trade(symbol, action, qty, entry, tp, sl):
    with open("trade_log.csv", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{symbol},{action},{qty},{entry},{tp},{sl}\n")

def send_telegram_alert(symbol, action, price, tp, sl):
    try:
        msg = f"🚨 {action} {symbol}\nPrice: {price}, TP: {tp}, SL: {sl}"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram error:", e)

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
        print("Email failed:", e)

# ✅ Multi-strategy signal
def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="20d", interval="1h")
        if len(df) < 30: return "HOLD"
        df["EMA20"] = df["Close"].ewm(span=20).mean()
        df["EMA50"] = df["Close"].ewm(span=50).mean()
        df["VolumeAvg"] = df["Volume"].rolling(window=20).mean()
        df["MACD"] = df["Close"].ewm(span=12).mean() - df["Close"].ewm(span=26).mean()

        ema_signal = df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1]
        volume_signal = df["Volume"].iloc[-1] > 1.2 * df["VolumeAvg"].iloc[-1]
        macd_signal = df["MACD"].iloc[-1] > 0

        if ema_signal and volume_signal and macd_signal:
            return "BUY"
        return "HOLD"
    except Exception as e:
        print(f"[ANALYSIS ERROR] {symbol}: {e}")
        return "HOLD"

def run_trading_bot(live=True, capital_per_trade=1000, tp_percent=2, sl_percent=1):
    funds = get_fyers_funds()
    try:
        available_cash = next((f["equityAmount"] for f in funds if f["title"] == "Total Cash"), 0)
    except:
        available_cash = 0

    for symbol in STOCK_LIST:
        signal = analyze_stock(symbol)
        if signal != "BUY":
            continue

        price = get_live_price(symbol)
        if price <= 0:
            continue

        qty = max(int(capital_per_trade // price), 1)
        total_cost = qty * price

        if live and total_cost > available_cash:
            print(f"⛔ Skipping {symbol}: Not enough funds.")
            continue

        tp_price = round(price * (1 + tp_percent / 100), 2)
        sl_price = round(price * (1 - sl_percent / 100), 2)

        if live:
            place_order(symbol, "BUY", qty)

        log_trade(symbol, "BUY", qty, price, tp_price, sl_price)
        send_telegram_alert(symbol, "BUY", price, tp_price, sl_price)

# ✅ PnL plot
def plot_trade_history():
    if not os.path.exists("trade_log.csv"):
        st.info("No trade history found.")
        return
    df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["PnL"] = df.apply(
        lambda x: (x["tp"] - x["entry"]) * x["qty"] if x["action"] == "BUY"
        else (x["entry"] - x["tp"]) * x["qty"], axis=1)
    df = df.sort_values("timestamp")
    df["CumulativePnL"] = df["PnL"].cumsum()
    st.subheader("📈 Cumulative Profit/Loss Chart")
    st.line_chart(df.set_index("timestamp")["CumulativePnL"])

def start_scheduler():
    schedule.every().day.at("09:15").do(lambda: run_trading_bot(live=True))
    schedule.every().day.at("16:30").do(send_trade_summary_email)
    threading.Thread(target=lambda: [schedule.run_pending() or time.sleep(60)], daemon=True).start()

def render_dashboard():
    st.set_page_config(layout="wide")
    st.title("📊 Smart AI Trading Dashboard")
    
    # Portfolio Positions
    st.subheader("📦 Current Positions (Fyers)")
    positions = get_fyers_positions()
    if positions:
        df_pos = pd.DataFrame(positions)
        st.dataframe(df_pos[["symbol", "netQty", "avgPrice", "pnl"]])
    else:
        st.info("No open positions available.")

    # Funds Available
    st.subheader("💰 Account Funds (Fyers)")
    funds = get_fyers_funds()
    if funds:
        df_fund = pd.DataFrame(funds)
        if not df_fund.empty:
            st.dataframe(df_fund[["title", "equityAmount", "collateralAmount", "net"]])
    else:
        st.warning("Could not fetch fund details.")

    # Profit / Loss chart
    st.subheader("📈 Cumulative PnL Chart")
    plot_trade_history()

    # Stock Analysis Insights
    st.subheader("🧠 Stock Insights (Multi-Strategy AI Signals)")
    if st.button("🔍 Analyze Nifty 500 Now"):
        selected_signals = []
        for symbol in STOCK_LIST[:20]:  # Limit to 20 for performance
            signal = analyze_stock(symbol)
            if signal == "BUY":
                selected_signals.append(symbol)
        if selected_signals:
            st.success(f"💡 Buy Signals: {', '.join(selected_signals)}")
        else:
            st.info("No BUY signals currently.")

# Start everything
start_scheduler()
render_dashboard()
