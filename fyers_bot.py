import os
import time
import pandas as pd
import streamlit as st
from fyers_apiv3 import fyersModel

# ✅ Load credentials securely from Streamlit secrets
APP_ID = st.secrets["FYERS"]["FYERS_APP_ID"]
ACCESS_TOKEN = st.secrets["FYERS"]["ACCESS_TOKEN"]

# ✅ Place order using Fyers API
def place_order(fyers, symbol, side, qty=1):
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
    print("\n[TRADE EXECUTED]", side, symbol, "| Response:", response)
    return response

# ✅ Run the AI trading bot
def run_trading_bot(signals_df, live=True):
    fyers = fyersModel.FyersModel(
        client_id=APP_ID,
        token=f"{APP_ID}:{ACCESS_TOKEN}",
        log_path="logs"
    )
    for _, row in signals_df.iterrows():
        symbol = row['symbol']
        action = row['signal']
        if action in ["BUY", "SELL"]:
            if live:
                place_order(fyers, symbol, action, qty=1)
            log_trade(symbol, action)

# ✅ Log trade history
def log_trade(symbol, action):
    with open("trade_log.csv", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{symbol},{action}\n")
