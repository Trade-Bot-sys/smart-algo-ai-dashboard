import os
import json
import requests

# ✅ Load secrets from environment
APP_ID = os.getenv("FYERS_APP_ID")
APP_SECRET = os.getenv("FYERS_APP_SECRET")
REFRESH_TOKEN = os.getenv("FYERS_REFRESH_TOKEN")
SESSION_PATH = "access_token.json"

# ✅ Generate new access token using refresh token
def refresh_access_token():
    print("🔄 Requesting new access token from Fyers API v3...")
    url = "https://api.fyers.in/api/v3/token"
    payload = {
        "grant_type": "refresh_token",
        "appIdHash": APP_ID,
        "secretKey": APP_SECRET,
        "refresh_token": REFRESH_TOKEN
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        if "access_token" not in data:
            raise Exception(f"Unexpected response: {data}")

        access_token = data["access_token"]
        with open(SESSION_PATH, "w") as f:
            json.dump({"app_id": APP_ID, "access_token": access_token}, f)

        print("✅ Access token saved to", SESSION_PATH)
        return True

    except Exception as e:
        print("❌ Token refresh failed:", e)
        return False

if __name__ == "__main__":
    refresh_access_token()
