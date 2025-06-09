import os
import json
import requests

# 🔐 Load credentials from environment
client_id = os.getenv("ANGEL_CLIENT_ID")
api_key = os.getenv("ANGEL_API_KEY")
mpin = os.getenv("ANGEL_MPIN")

print("📨 Logging in with client:", client_id)

# 🌐 Endpoint
url = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByMpin"

# 📦 Headers
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-UserType": "USER",
    "X-SourceID": "WEB",
    "X-ClientLocalIP": "127.0.0.1",
    "X-ClientPublicIP": "127.0.0.1",
    "X-MACAddress": "AA:BB:CC:DD:EE:FF",
    "X-PrivateKey": api_key
}

# 📨 Payload
payload = {
    "clientcode": client_id,
    "mpin": mpin
}

# 🔄 Request
response = requests.post(url, headers=headers, json=payload)

try:
    data = response.json()
    print("📦 Full response:", json.dumps(data, indent=2))

    if not data.get("status"):
        raise Exception(f"Login failed: {data.get('message')}")

    access_token = data["data"]["jwtToken"]
    with open("access_token.json", "w") as f:
        json.dump({
            "client_id": client_id,
            "access_token": access_token
        }, f)

    print("✅ Access token saved successfully!")

except json.JSONDecodeError:
    print("❌ Failed to parse JSON. Raw response:")
    print(response.text)
except Exception as e:
    print("❌ Login failed:", e)
