import os
import json
import pyotp
from smartapi.smartConnect import SmartConnect

# ✅ Load credentials from env (GitHub Actions or .env)
api_key = os.getenv("ANGEL_API_KEY")
client_code = os.getenv("ANGEL_CLIENT_ID")
totp_secret = os.getenv("ANGEL_TOTP_SECRET")

# ✅ Generate current TOTP
totp = pyotp.TOTP(totp_secret).now()

# ✅ Initialize SmartConnect and generate session
try:
    obj = SmartConnect(api_key)
    session_data = obj.generateSession(client_code, totp)
    access_token = session_data["data"]["access_token"]

    # ✅ Save access token to JSON file
    with open("access_token.json", "w") as f:
        json.dump({
            "client_id": client_code,
            "access_token": access_token
        }, f)

    print("✅ Access token generated and saved.")
except Exception as e:
    print("❌ Error generating token:", e)
    import traceback
    traceback.print_exc()
