import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from fyers_apiv3.FyersWeb import accessToken  # ✅ Corrected import

# ✅ Replace with your Fyers app credentials
APP_ID = "YOUR_APP_ID"
APP_SECRET = "YOUR_APP_SECRET"
REDIRECT_URI = "https://YOUR-REDIRECT-URL.com"
USERNAME = "YOUR_MOBILE_OR_EMAIL"
PASSWORD = "YOUR_PASSWORD"
PIN = "123456"  # Your 6-digit pin
SESSION_PATH = "access_token.json"

# ✅ Step 1: Generate auth URL
AUTH_URL = f"https://api.fyers.in/api/v2/generate-authcode?client_id={APP_ID}&redirect_uri={REDIRECT_URI}&response_type=code&state=sample"

# ✅ Step 2: Launch headless Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=chrome_options)

try:
    driver.get(AUTH_URL)
    time.sleep(2)

    # Enter username & password
    driver.find_element(By.ID, "fy_username").send_keys(USERNAME)
    driver.find_element(By.ID, "loginSubmit").click()
    time.sleep(2)

    driver.find_element(By.ID, "fy_password").send_keys(PASSWORD)
    driver.find_element(By.ID, "loginSubmit").click()
    time.sleep(2)

    # Enter PIN
    for i, digit in enumerate(PIN, 1):
        driver.find_element(By.ID, f"pin{i}").send_keys(digit)
    driver.find_element(By.ID, "loginSubmit").click()
    time.sleep(3)

    # ✅ Get auth_code from redirected URL
    final_url = driver.current_url
    if "auth_code=" not in final_url:
        raise Exception("Auth code not found in URL. Login may have failed.")
    auth_code = final_url.split("auth_code=")[-1]

    # ✅ Step 3: Exchange auth_code for access_token
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

    # ✅ Step 4: Save token to file
    with open(SESSION_PATH, "w") as f:
        json.dump({
            "app_id": APP_ID,
            "access_token": access_token
        }, f)

    print("✅ Access token generated and saved.")

except Exception as e:
    print("❌ Failed to generate token:", e)
finally:
    driver.quit()
