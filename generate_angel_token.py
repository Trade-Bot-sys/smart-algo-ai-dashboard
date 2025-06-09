import os
import json
import pyotp
from smartapi.smartConnect import SmartConnect  # ✅ Use lowercase "smartapi"

# 🔐 Load credentials from GitHub Actions secrets/environment
client_id = os.getenv("ANGEL_CLIENT_ID")
password = os.getenv("ANGEL_PASSWORD")
api_key = os.getenv("ANGEL_API_KEY")
totp_key = os.getenv("ANGEL_TOTP_SECRET")

# ✅ Generate dynamic TOTP
totp = pyotp.TOTP(totp_key).now()

# ✅ Connect to Angel One
obj = SmartConnect(api_key=api_key)
data = obj.generateSession(client_id, password, totp)

# ✅ Extract access token
access_token = data["data"]["access_token"]

# ✅ Save token to file
with open("access_token.json", "w") as f:
    json.dump({"client_id": client_id, "access_token": access_token}, f)

print("✅ Angel access token generated and saved!")
