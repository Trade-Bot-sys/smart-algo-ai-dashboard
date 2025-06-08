import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from fyers_apiv3 import accessToken

# Replace these values with your Fyers credentials
APP_ID = "YOUR_APP_ID"
APP_SECRET = "YOUR_APP_SECRET"
REDIRECT_URI = "https://YOUR-REDIRECT-URL.com"
USERNAME = "YOUR_FYERS_USERID"
PASSWORD = "YOUR_FYERS_PASSWORD"
PIN = "YOUR_6_DIGIT_PIN"
SESSION_PATH = "access_token.json"

# Generate auth URL
AUTH_URL = f"https://api.fyers.in/api/v2/generate-authcode?client_id={APP_ID}&redirect_uri={REDIRECT_URI}&response_type=code&state=state123"

# Configure headless browser
chrome_options = Options()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(options=chrome_options)

try:
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

    auth_code = driver.current_url.split("auth_code=")[-1]

    # Exchange for access token
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

    # Save access token
    with open(SESSION_PATH, "w") as f:
        json.dump({
            "app_id": APP_ID,
            "access_token": access_token
        }, f)

    print("✅ Access token saved to", SESSION_PATH)

except Exception as e:
    print("❌ Failed to get token:", e)
finally:
    driver.quit()
