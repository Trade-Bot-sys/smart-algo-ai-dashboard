# 📈 Smart AI Trading Dashboard (Expanded Version with Full Features)
import streamlit as st
st.set_page_config(layout="wide", page_title="Smart AI Trading Dashboard")
st.title("📈 Smart AI Trading Dashboard")

import os
import smtplib
from email.message import EmailMessage
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from apscheduler.schedulers.background import BackgroundScheduler
from googlesearch import search
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersModel import accessToken
from fyers_bot import (
    run_trading_bot,
    get_fyers_positions,
    get_fyers_funds,
    send_telegram_alert,
    send_trade_summary_email
)

# other imports...

# ✅ Load Streamlit secrets
APP_ID = st.secrets["FYERS"]["FYERS_APP_ID"]
ACCESS_TOKEN = st.secrets["FYERS"]["ACCESS_TOKEN"]
EMAIL = st.secrets["EMAIL"]["EMAIL_ADDRESS"]
EMAIL_PASS = st.secrets["EMAIL"]["EMAIL_PASSWORD"]
TELEGRAM_TOKEN = st.secrets["ALERTS"]["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["ALERTS"]["TELEGRAM_CHAT_ID"]

# ✅ Generate or load access token
@st.cache_data(ttl=3600)
def generate_access_token():
    session = accessToken.SessionModel(
        client_id=APP_ID,
        secret_key=APP_SECRET,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code"
    )
    session.set_token(st.secrets["FYERS"]["AUTH_CODE"])
    response = session.generate_token()
    access_token = response["access_token"]
    with open("access_token.txt", "w") as f:
        f.write(access_token)
    return access_token

if os.path.exists("access_token.txt"):
    with open("access_token.txt") as f:
        ACCESS_TOKEN = f.read().strip()
else:
    ACCESS_TOKEN = generate_access_token()

# ✅ Setup Fyers session
fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=f"{APP_ID}:{ACCESS_TOKEN}",
    log_path="logs/"
)

# ✅ Setup Fyers session
fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=f"{APP_ID}:{ACCESS_TOKEN}",
    log_path="logs/"
)

# ✅ Load Nifty 500 stock list
try:
    nifty_df = pd.read_csv("data/nifty500list.csv")
    STOCK_LIST = [f"{s}.NS" for s in nifty_df["Symbol"].dropna()]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

# ✅ Google News Sentiment Analysis
@st.cache_data(ttl=3600)
def news_sentiment_score(symbol):
    query = f"{symbol} stock news site:moneycontrol.com OR site:economictimes.indiatimes.com"
    try:
        return len(list(search(query, num_results=5)))
    except:
        return 0

@st.cache_data(ttl=3600)
def get_top_news_stocks():
    results = []
    for s in STOCK_LIST[:50]:
        score = news_sentiment_score(s.replace(".NS", ""))
        results.append((s, score))
    sorted_stocks = sorted(results, key=lambda x: x[1], reverse=True)
    return [s[0] for s in sorted_stocks[:5]]

# ✅ AI Strategy Signal
@st.cache_data(ttl=600)
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

        return "BUY" if ema_signal and volume_signal and macd_signal else "HOLD"
    except:
        return "HOLD"

# ✅ UI: Smart Dashboard

# Inputs
capital = st.number_input("Capital per Trade (₹)", value=1000)
tp = st.slider("Take Profit %", 1, 10, value=2)
sl = st.slider("Stop Loss %", 1, 10, value=1)

# Get recommended stock from news + strategy
top_stocks = get_top_news_stocks()
symbol = top_stocks[0] if top_stocks else "RELIANCE.NS"
signal = get_strategy_signal(symbol)
data = yf.download(symbol, period="3mo", interval="1d")
data['Signal'] = ["HOLD"] * len(data)
data.loc[data.index[-1], 'Signal'] = signal

# Show Signal + Chart
st.subheader(f"📍 Signal for {symbol}: {signal}")
fig = go.Figure()
fig.add_candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])
if signal == "BUY":
    fig.add_trace(go.Scatter(x=[data.index[-1]], y=[data['Close'].iloc[-1]], mode="markers", marker=dict(color="green", size=12), name="BUY"))
st.plotly_chart(fig)

# ✅ Scheduler (Auto at 9:15 and 4:30)
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
    st.toast("✅ Auto trading and summary scheduled")

# ✅ Portfolio Display
st.header("📦 Live Portfolio")
positions = get_fyers_positions()
if positions:
    df_positions = pd.DataFrame(positions)
    df_positions["PnL ₹"] = df_positions["netQty"] * (df_positions["ltp"] - df_positions["avgPrice"])
    st.dataframe(df_positions[["symbol", "netQty", "avgPrice", "ltp", "PnL ₹"]])
else:
    st.info("No open positions.")

# ✅ Funds Display
st.header("💰 Available Funds")
funds = get_fyers_funds()
if funds:
    df_funds = pd.DataFrame(funds)
    st.dataframe(df_funds[["title", "equityAmount", "collateralAmount", "net"]])
else:
    st.warning("Funds unavailable")

# ✅ Cumulative PnL Chart
st.header("📊 PnL History")
if os.path.exists("trade_log.csv"):
    df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna()
    df["PnL"] = df.apply(lambda x: (x["tp"] - x["entry"]) * x["qty"] if x["action"] == "BUY" else (x["entry"] - x["tp"]) * x["qty"], axis=1)
    df = df.sort_values("timestamp")
    df["CumulativePnL"] = df["PnL"].cumsum()
    st.line_chart(df.set_index("timestamp")["CumulativePnL"])
    
    # 🔄 Use df instead of df_log
    stock_options = df["symbol"].dropna().unique().tolist()
    selected_stock = st.selectbox("Select Stock", stock_options, index=0 if stock_options else None)

if selected_stock:
    try:
        hist_data = yf.download(selected_stock, period="2mo", interval="1d")
        if not hist_data.empty:
            fig2 = go.Figure()
            fig2.add_candlestick(
                x=hist_data.index,
                open=hist_data["Open"],
                high=hist_data["High"],
                low=hist_data["Low"],
                close=hist_data["Close"]
            )
            
            # Plot past trades for this stock
            stock_trades = df_log[df_log["symbol"] == selected_stock]
            for _, row in stock_trades.iterrows():
                color = "green" if row["action"] == "BUY" else "red"
                label = row["action"].capitalize()
                fig2.add_trace(go.Scatter(
                    x=[row["timestamp"]],
                    y=[row["entry"]],
                    mode="markers+text",
                    marker=dict(color=color, size=10),
                    name=label,
                    text=[label],
                    textposition="top center" if row["action"] == "BUY" else "bottom center"
                ))
            st.subheader(f"📈 Trade Log Chart - {selected_stock}")
            st.plotly_chart(fig2)
        else:
            st.warning("⚠️ No historical data found for selected stock.")
    except Exception as e:
        st.error(f"⚠️ Error loading chart: {e}")

# ✅ Live Trade Chart Per Stock with Dropdown
st.header("📌 Trade History by Stock")
if os.path.exists("trade_log.csv"):
    df_log = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
    df_log["timestamp"] = pd.to_datetime(df_log["timestamp"], errors="coerce")
    df_log = df_log.dropna()
    
    
# ✅ Telegram Test
if st.button("🔔 Test Telegram Alert"):
    send_telegram_alert("TEST", "BUY", 100, 102, 98)
    st.success("Telegram alert sent!")

# ✅ Manual Summary Send
if st.button("📤 Send Daily Summary Now"):
    send_trade_summary_email()
    st.success("📧 Summary email sent!")
