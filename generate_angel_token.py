import os
import json
import pyotp
import requests

# Load from environment
api_key = os.getenv("ANGEL_API_KEY")
client_code = os.getenv("ANGEL_CLIENT_ID")
totp_secret = os.getenv("ANGEL_TOTP_SECRET")

totp = pyotp.TOTP(totp_secret).now()
print("🔐 TOTP:", totp)

url = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword"

headers = {
    "X-ClientLocalIP": "127.0.0.1",
    "X-ClientPublicIP": "127.0.0.1",
    "X-MACAddress": "AA:BB:CC:DD:EE:FF",
    "X-PrivateKey": api_key,
    "X-UserType": "USER",
    "X-SourceID": "WEB",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

payload = {
    "clientcode": client_code,
    "password": totp  # TOTP as password
}

response = requests.post(url, headers=headers, json=payload)

try:
    data = response.json()
    print("📦 Full response:", json.dumps(data, indent=2))
    if not data.get("status"):
        raise Exception(f"Login failed: {data.get('message')}")

    access_token = data["data"]["jwtToken"]
    with open("access_token.json", "w") as f:
        json.dump({"client_id": client_code, "access_token": access_token}, f)

    print("✅ Access token saved.")
except Exception as e:
    print("❌ Login failed:", e)
