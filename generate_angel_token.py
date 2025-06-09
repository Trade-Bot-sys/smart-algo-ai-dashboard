import os
import json
import requests

# ✅ Load from environment variables
api_key = os.getenv("ANGEL_API_KEY")
client_code = os.getenv("ANGEL_CLIENT_ID")
mpin = os.getenv("ANGEL_MPIN")  # 🔐 NEW: MPIN from your Angel One app

# ✅ Angel login URL (Login by MPIN)
url = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByMpin"

# ✅ Required headers
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

# ✅ Payload with MPIN
payload = {
    "clientcode": client_code,
    "mpin": mpin
}

# ✅ Send request
print("📨 Logging in with client:", client_code)
response = requests.post(url, headers=headers, json=payload)

try:
    data = response.json()
    print("📦 Response:", json.dumps(data, indent=2))

    if not data.get("status"):
        raise Exception(f"Login failed: {data.get('message')}")

    access_token = data["data"]["jwtToken"]
    with open("access_token.json", "w") as f:
        json.dump({
            "client_id": client_code,
            "access_token": access_token
        }, f)

    print("✅ Access token saved successfully!")

except Exception as e:
    print("❌ Login failed:", e)
