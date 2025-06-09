import os, json, pyotp
from SmartApi import SmartConnect

client_id = os.getenv("ANGEL_CLIENT_ID")
password = os.getenv("ANGEL_PASSWORD")
api_key = os.getenv("ANGEL_API_KEY")
totp_key = os.getenv("ANGEL_TOTP_SECRET")

# ✅ Generate TOTP
totp = pyotp.TOTP(totp_key).now()

# ✅ Authenticate
obj = SmartConnect(api_key)
data = obj.generateSession(client_id, password, totp)
access_token = data['data']['access_token']

# ✅ Save token
with open("access_token.json", "w") as f:
    json.dump({"client_id": client_id, "access_token": access_token}, f)

print("✅ Token generated and saved!")
