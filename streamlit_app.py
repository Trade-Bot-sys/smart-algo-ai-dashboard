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
from fyers_bot import run_trading_bot, get_fyers_positions, get_fyers_funds, send_telegram_alert

# Load secrets
APP_ID = st.secrets["FYERS"]["FYERS_APP_ID"]
ACCESS_TOKEN = st.secrets["FYERS"]["ACCESS_TOKEN"]
EMAIL = st.secrets["EMAIL"]["EMAIL_ADDRESS"]
EMAIL_PASS = st.secrets["EMAIL"]["EMAIL_PASSWORD"]
TELEGRAM_TOKEN = st.secrets["ALERTS"]["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["ALERTS"]["TELEGRAM_CHAT_ID"]

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

# Signal analysis
@st.cache_data(ttl=3600)
def get_strategy_signal(symbol):
    try:
        df = yf.download(symbol, period="15d", interval="1h")
        if len(df) < 30:
            return "HOLD"
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
    except:
        return "HOLD"

# 📊 UI Start
st.title("📈 Smart AI Trading Dashboard with Live News & Strategy")

# Trade params
capital = st.number_input("Capital per Trade (₹)", value=1000)
tp = st.slider("Take Profit %", 1, 10, value=2)
sl = st.slider("Stop Loss %", 1, 10, value=1)

# Display signal stock from news
top_stocks = get_top_news_stocks()
symbol = top_stocks[0] if top_stocks else "RELIANCE.NS"
data = yf.download(symbol, period="3mo", interval="1d")
signal = get_strategy_signal(symbol)
data['Signal'] = ["HOLD"] * len(data)
data.loc[data.index[-1], 'Signal'] = signal

st.subheader(f"📍 Signal for {symbol}: {signal}")
fig = go.Figure()
fig.add_candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])
last_price = data['Close'].iloc[-1]
if signal == "BUY":
    fig.add_trace(go.Scatter(x=[data.index[-1]], y=[last_price], mode="markers", marker=dict(color="green", size=12), name="BUY Signal"))
st.plotly_chart(fig)

# Auto run trade at 9:15 AM with stop loss and take profit
if "scheduler_started" not in st.session_state:
    def auto_trade():
        signal_df = pd.DataFrame([{"symbol": symbol, "signal": get_strategy_signal(symbol)}])
        run_trading_bot(signal_df, live=True, capital_per_trade=capital, tp_percent=tp, sl_percent=sl)

    def auto_summary():
        send_trade_summary_email()

    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(auto_trade, "cron", hour=9, minute=15)
    scheduler.add_job(auto_summary, "cron", hour=16, minute=30)
    scheduler.start()
    st.session_state.scheduler_started = True
    st.toast("✅ Trade & Summary Scheduler Set: 9:15 AM & 4:30 PM IST")

# Live positions
st.header("📦 Portfolio (Fyers)")
positions = get_fyers_positions()
if positions:
    df_positions = pd.DataFrame(positions)
    df_positions["PnL ₹"] = df_positions["netQty"] * (df_positions["ltp"] - df_positions["avgPrice"])
    st.dataframe(df_positions[["symbol", "netQty", "avgPrice", "ltp", "PnL ₹"]])
else:
    st.info("No open positions.")

# Available funds
st.header("💰 Funds (Fyers)")
funds = get_fyers_funds()
if funds:
    df_funds = pd.DataFrame(funds)
    st.dataframe(df_funds[["title", "equityAmount", "collateralAmount", "net"]])
else:
    st.warning("Unable to fetch fund details.")

# Trade summary chart
st.subheader("📈 Cumulative PnL Chart")
if os.path.exists("trade_log.csv"):
    try:
        df_log = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
        df_log["timestamp"] = pd.to_datetime(df_log["timestamp"], errors="coerce")
        df_log = df_log.dropna()
        df_log["PnL"] = df_log.apply(lambda x: (x["tp"] - x["entry"]) * x["qty"] if x["action"] == "BUY" else (x["entry"] - x["tp"]) * x["qty"], axis=1)
        df_log = df_log.sort_values("timestamp")
        df_log["CumulativePnL"] = df_log["PnL"].cumsum()
        st.line_chart(df_log.set_index("timestamp")["CumulativePnL"])
    except Exception as e:
        st.warning(f"Chart error: {e}")

# Telegram test button
if st.button("🔔 Test Telegram Alert"):
    send_telegram_alert("TEST", "BUY", 100, 102, 98)
    st.success("✅ Telegram alert sent!")

# Email summary manually
if st.button("📤 Send Daily Trade Summary Now"):
    send_trade_summary_email()
    st.success("📨 Summary email sent successfully!")
