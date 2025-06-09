import os
import json
import pyotp
from smartapi.smartConnect import SmartConnect

# ✅ Load credentials from environment
api_key = os.getenv("ANGEL_API_KEY")
client_code = os.getenv("ANGEL_CLIENT_ID")
pin = os.getenv("ANGEL_PASSWORD")  # 🔑 This is your Angel One login PIN
totp_secret = os.getenv("ANGEL_TOTP_SECRET")

# ✅ Generate TOTP
totp = pyotp.TOTP(totp_secret).now()
print("🔐 TOTP:", totp)

# ✅ Authenticate with SmartAPI
try:
    obj = SmartConnect(api_key=api_key)
    print(f"📨 Logging in as: {client_code}")

    session = obj.generateSession(client_code, pin, totp)
    print("📦 Full response:", json.dumps(session, indent=2))

    if not session or not session.get("data"):
        raise Exception("Login failed or missing token.")

    access_token = session["data"]["access_token"]
    with open("access_token.json", "w") as f:
        json.dump({
            "client_id": client_code,
            "access_token": access_token
        }, f)

    print("✅ Access token saved successfully.")

except Exception as e:
    print("❌ Error generating token:", e)
