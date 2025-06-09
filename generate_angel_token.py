import os, json, pyotp
from smartapi.smartConnect import SmartConnect

# ✅ Load from environment
api_key = os.getenv("ANGEL_API_KEY")
client_code = os.getenv("ANGEL_CLIENT_ID")
totp_secret = os.getenv("ANGEL_TOTP_SECRET")

# ✅ Generate TOTP
totp = pyotp.TOTP(totp_secret).now()

try:
    obj = SmartConnect(api_key)
    print("📨 Logging in with:", client_code)
    print("🔐 Using TOTP:", totp)

    session_data = obj.generateSession(client_code, totp)

    print("📦 Raw session response:", session_data)

    # ✅ Validate response
    if not session_data or "data" not in session_data:
        raise Exception("Login failed or invalid session response.")

    access_token = session_data["data"]["access_token"]

    # ✅ Save access token
    with open("access_token.json", "w") as f:
        json.dump({
            "client_id": client_code,
            "access_token": access_token
        }, f)

    print("✅ Access token saved to access_token.json")

except Exception as e:
    print("❌ Error generating token:", e)
