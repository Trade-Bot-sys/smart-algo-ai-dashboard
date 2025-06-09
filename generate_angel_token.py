import os, json, pyotp
from smartapi.smartConnect import SmartConnect

api_key = os.getenv("ANGEL_API_KEY")
client_code = os.getenv("ANGEL_CLIENT_ID")
totp_secret = os.getenv("ANGEL_TOTP_SECRET")

totp = pyotp.TOTP(totp_secret).now()

try:
    obj = SmartConnect(api_key)
    print("📨 Logging in with:", client_code, api_key)
    print("🔐 Using TOTP:", totp)

    session_data = obj.generateSession(client_code, totp)
    print("📦 Raw session response:", session_data)

    access_token = session_data["data"]["access_token"]  # ❗ This line failed
    with open("access_token.json", "w") as f:
        json.dump({"client_id": client_code, "access_token": access_token}, f)

    print("✅ Token saved to access_token.json")

except Exception as e:
    print("❌ Error generating token:", e)
