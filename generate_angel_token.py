import os
import json
import pyotp
from smartapi.smartConnect import SmartConnect

# ✅ Load credentials from GitHub Actions secrets/environment
client_id = os.getenv("ANGEL_CLIENT_ID")
password = os.getenv("ANGEL_PASSWORD")
api_key = os.getenv("ANGEL_API_KEY")
totp_secret = os.getenv("ANGEL_TOTP_SECRET")

# ✅ Generate TOTP
totp = pyotp.TOTP(totp_secret).now()

# ✅ Initialize SmartConnect
obj = SmartConnect(api_key)

# ✅ Generate session using positional arguments (required in SmartAPI v1.1.0)
try:
    session_data = obj.generateSession(client_id, password, totp)
    access_token = session_data["data"]["access_token"]

    # ✅ Save access token to file
    with open("access_token.json", "w") as f:
        json.dump({
            "client_id": client_id,
            "access_token": access_token
        }, f)

    print("✅ Access token generated and saved successfully.")
except Exception as e:
    print("❌ Failed to generate token:", e)
