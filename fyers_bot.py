import os
import time
import pandas as pd
import streamlit as st
from fyers_apiv3 import fyersModel
from fyers_apiv3.fyers_app import FyersApp  # ✅ Correct import

# Load credentials securely from Streamlit secrets
APP_ID = st.secrets["FYERS"]["FYERS_APP_ID"]
APP_SECRET = st.secrets["FYERS"]["FYERS_APP_SECRET"]
REDIRECT_URI = st.secrets["FYERS"]["FYERS_REDIRECT_URI"]
ACCESS_TOKEN_PATH = "access_token.txt"

# Generate new access token (manual step required)
def generate_access_token():
    app = FyersApp(
        client_id=APP_ID,
        secret_key=APP_SECRET,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code"
    )
    auth_url = app.generate_authcode()
    print("\n[INFO] Login here and get the auth code:")
    print(auth_url)
    auth_code = input("\nPaste the auth code: ")
    app.set_token(auth_code)
    token_response = app.generate_token()
    access_token = token_response["access_token"]
    with open(ACCESS_TOKEN_PATH, 'w') as f:
        f.write(access_token)
    return access_token

# Load or generate token
def load_access_token():
    if os.path.exists(ACCESS_TOKEN_PATH):
        with open(ACCESS_TOKEN_PATH, 'r') as f:
            return f.read().strip()
    else:
        st.warning("Access token not found. Please generate it locally using terminal.")
        raise RuntimeError("Access token not available on Streamlit Cloud. Generate it locally first.")

# Place order using Fyers API
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

# Execute trading strategy
def run_trading_bot(signals_df, live=True):
    access_token = load_access_token()
    fyers = fyersModel.FyersModel(
        client_id=APP_ID,
        token=f"{APP_ID}:{access_token}",
        log_path="logs"
    )
    for _, row in signals_df.iterrows():
        symbol = row['symbol']
        action = row['signal']
        if action in ["BUY", "SELL"]:
            if live:
                place_order(fyers, symbol, action, qty=1)
            log_trade(symbol, action)

# Log executed trades
def log_trade(symbol, action):
    with open("trade_log.csv", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{symbol},{action}\n")
