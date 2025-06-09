import os, json, pyotp
from smartapi.smartConnect import SmartConnect

api_key = os.getenv("ANGEL_API_KEY")
client_code = os.getenv("ANGEL_CLIENT_ID")
totp_secret = os.getenv("ANGEL_TOTP_SECRET")

totp = pyotp.TOTP(totp_secret).now()
print("🔐 TOTP:", totp)

try:
    obj = SmartConnect(api_key)
    print("📨 Logging in with:", client_code)

    session_data = obj.generateSession(client_code, totp)

    if session_data is None:
        raise Exception("Login failed: No session response received")

    print("📦 Full session response:")
    print(json.dumps(session_data, indent=2))

    access_token = session_data["data"]["access_token"]

    with open("access_token.json", "w") as f:
        json.dump({
            "client_id": client_code,
            "access_token": access_token
        }, f)

    print("✅ Token saved successfully!")

except Exception as e:
    print("❌ Error generating token:", e)
