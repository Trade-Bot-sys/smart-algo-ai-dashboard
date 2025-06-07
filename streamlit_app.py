os.makedirs("logs", exist_ok=True)
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

capital = st.number_input("Capital per trade (₹)", value=1000)
tp = st.slider("Take Profit %", 1, 10, value=2)
sl = st.slider("Stop Loss %", 1, 10, value=1)

if st.button("Run AI Trade Now"):
    signal_df = pd.DataFrame([{"symbol": symbol, "signal": data['Signal']}])
    run_trading_bot(signal_df, live=live_mode, capital_per_trade=capital, tp_percent=tp, sl_percent=sl)
    st.success("Trade processed in " + ("Live" if live_mode else "Simulation") + " mode.")
  
from fyers_bot import run_trading_bot

st.title("📊 Smart AI Trading Dashboard (Live Fyers Mode)")

mode = st.radio("Select Trading Mode:", ["Simulation", "Live Trading"], index=0)
live_mode = mode == "Live Trading"

stocks = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]
symbol = st.selectbox("Choose Stock:", stocks)

data = yf.download(symbol, period="3mo", interval="1d")
data['Signal'] = ["HOLD"] * len(data)
data['Signal'].iloc[-1] = "BUY"
st.write("## Signal: ", data['Signal'].iloc[-1])

fig = go.Figure()
fig.add_candlestick(x=data.index,
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'])

last_price = data['Close'].iloc[-1]
if data['Signal'].iloc[-1] == "BUY":
    fig.add_trace(go.Scatter(x=[data.index[-1]], y=[last_price], mode="markers", marker=dict(color="green", size=12), name="BUY"))
elif data['Signal'].iloc[-1] == "SELL":
    fig.add_trace(go.Scatter(x=[data.index[-1]], y=[last_price], mode="markers", marker=dict(color="red", size=12), name="SELL"))

st.plotly_chart(fig)

if st.button("Run AI Trade Now"):
    signal_df = pd.DataFrame([{"symbol": symbol, "signal": data['Signal'].iloc[-1]}])
    run_trading_bot(signal_df, live=live_mode)
    st.success("Trade processed in " + ("Live" if live_mode else "Simulation") + " mode!")
