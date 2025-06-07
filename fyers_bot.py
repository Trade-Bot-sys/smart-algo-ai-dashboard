import os import time import pandas as pd import streamlit as st from fyers_apiv3 import fyersModel from fyers_apiv3 import accessToken import requests

Load credentials securely from Streamlit secrets

APP_ID = st.secrets["FYERS"]["FYERS_APP_ID"] APP_SECRET = st.secrets["FYERS"]["FYERS_APP_SECRET"] REDIRECT_URI = st.secrets["FYERS"]["FYERS_REDIRECT_URI"] ACCESS_TOKEN = st.secrets["FYERS"]["ACCESS_TOKEN"]

Get live market price

@st.cache_data(ttl=60) def get_live_price(symbol): try: data = { "symbols": symbol } headers = {"Authorization": f"Bearer {APP_ID}:{ACCESS_TOKEN}"} response = requests.get("https://api.fyers.in/data-rest/v2/quotes", params=data, headers=headers) res_json = response.json() return res_json['d'][0]['v']['lp']  # Last traded price except: return 0

Place order using Fyers API

def place_order(fyers, symbol, side, qty): order = { "symbol": symbol, "qty": qty, "type": 2,  # MARKET "side": 1 if side == "BUY" else -1, "productType": "INTRADAY", "limitPrice": 0, "stopPrice": 0, "validity": "DAY", "disclosedQty": 0, "offlineOrder": False, "orderType": 1  # MARKET } response = fyers.place_order(order) print("[TRADE EXECUTED]", side, symbol, "| Qty:", qty, "| Response:", response) return response

Log executed trades

def log_trade(symbol, action, qty, entry_price, tp_price, sl_price): with open("trade_log.csv", "a") as f: f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{symbol},{action},{qty},{entry_price},{tp_price},{sl_price}\n")

Main trading function

def run_trading_bot(signals_df, live=True, capital_per_trade=10000, tp_percent=2, sl_percent=1): fyers = fyersModel.FyersModel( client_id=APP_ID, token=f"{APP_ID}:{ACCESS_TOKEN}", log_path="logs/" )

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
            place_order(fyers, symbol, action, qty)

        log_trade(symbol, action, qty, price, tp_price, sl_price)

