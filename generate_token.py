import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from fyers_apiv3 import accessToken

# ✅ Load from Render environment variables
APP_ID = os.getenv("FYERS_APP_ID")
APP_SECRET = os.getenv("FYERS_APP_SECRET")
REDIRECT_URI = os.getenv("FYERS_REDIRECT_URI")
USERNAME = os.getenv("FYERS_USERNAME")
PASSWORD = os.getenv("FYERS_PASSWORD")
PIN = os.getenv("FYERS_PIN")
SESSION_PATH = "access_token.json"  # This file will be read by your bot

# ✅ Generate the auth URL
AUTH_URL = f"https://api.fyers.in/api/v2/generate-authcode?client_id={APP_ID}&redirect_uri={REDIRECT_URI}&response_type=code&state=state123"

# ✅ Configure headless Chrome (works on Render)
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=chrome_options)

try:
    print("🚀 Logging in to Fyers...")
    driver.get(AUTH_URL)
    time.sleep(3)

    driver.find_element(By.ID, "fy_username").send_keys(USERNAME)
    driver.find_element(By.ID, "loginSubmit").click()
    time.sleep(2)

    driver.find_element(By.ID, "fy_password").send_keys(PASSWORD)
    driver.find_element(By.ID, "loginSubmit").click()
    time.sleep(2)

    for i, digit in enumerate(PIN, 1):
        driver.find_element(By.ID, f"pin{i}").send_keys(digit)
    driver.find_element(By.ID, "loginSubmit").click()
    time.sleep(4)

    current_url = driver.current_url
    if "auth_code=" not in current_url:
        raise Exception("❌ Login failed or Auth code not found.")

    auth_code = current_url.split("auth_code=")[-1]

    # ✅ Exchange auth code for access token
    session = accessToken.SessionModel(
        client_id=APP_ID,
        secret_key=APP_SECRET,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code"
    )
    session.set_token(auth_code)
    token_response = session.generate_token()
    access_token = token_response["access_token"]

    # ✅ Save to file
    with open(SESSION_PATH, "w") as f:
        json.dump({
            "app_id": APP_ID,
            "access_token": access_token
        }, f)

    print("✅ Access token saved to", SESSION_PATH)

except Exception as e:
    print("❌ Error during token generation:", e)
finally:
    driver.quit()
