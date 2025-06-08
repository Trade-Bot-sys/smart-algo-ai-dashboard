import os
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import telebot

# ✅ Load from environment
APP_ID = os.getenv("FYERS_APP_ID")
APP_SECRET = os.getenv("FYERS_APP_SECRET")
REDIRECT_URI = os.getenv("FYERS_REDIRECT_URI")
USERNAME = os.getenv("FYERS_USERNAME")
PASSWORD = os.getenv("FYERS_PASSWORD")
PIN = os.getenv("FYERS_PIN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SESSION_PATH = "access_token.json"

def refresh_token():
    try:
        print("🔄 Launching headless browser...")
        auth_url = f"https://api.fyers.in/api/v2/generate-authcode?client_id={APP_ID}&redirect_uri={REDIRECT_URI}&response_type=code&state=state123"

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")  # ✅ Ensure proper page rendering

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(20)

        print("🌐 Navigating to Fyers auth page...")
        driver.get(auth_url)
        time.sleep(3)
        driver.save_screenshot("step1_loaded.png")  # ✅ Screenshot for debug

        print("📝 Entering username...")
        driver.find_element(By.ID, "fy_username").send_keys(USERNAME)
        driver.find_element(By.ID, "loginSubmit").click()
        time.sleep(2)
        driver.save_screenshot("step2_username.png")

        print("🔐 Entering password...")
        driver.find_element(By.ID, "fy_password").send_keys(PASSWORD)
        driver.find_element(By.ID, "loginSubmit").click()
        time.sleep(2)
        driver.save_screenshot("step3_password.png")

        print("🔢 Entering PIN...")
        for i, d in enumerate(PIN, 1):
            driver.find_element(By.ID, f"pin{i}").send_keys(d)
        driver.find_element(By.ID, "loginSubmit").click()
        time.sleep(4)
        driver.save_screenshot("step4_pin.png")

        print("📦 Checking for auth code in URL...")
        if "auth_code=" not in driver.current_url:
            driver.save_screenshot("error_no_auth_code.png")  # 👀 Capture failure
            raise Exception("❌ Auth code not found. Login might have failed.")

        auth_code = driver.current_url.split("auth_code=")[-1]
        print("✅ Auth code received:", auth_code[:10], "...")

        # Continue to exchange token...
        session = accessToken.SessionModel(
            client_id=APP_ID,
            secret_key=APP_SECRET,
            redirect_uri=REDIRECT_URI,
            response_type="code",
            grant_type="authorization_code"
        )
        session.set_token(auth_code)
        response = session.generate_token()

        access_token = response["access_token"]
        with open(SESSION_PATH, "w") as f:
            json.dump({"app_id": APP_ID, "access_token": access_token}, f)

        print("✅ Access token saved to", SESSION_PATH)
        return True

    except Exception as e:
        print("❌ Exception occurred during token generation:", e)
        driver.save_screenshot("token_error.png")
        return False

    finally:
        try:
            driver.quit()
        except:
            pass

# ✅ Telegram Bot Handler
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=["refresh"])
def manual_refresh(message):
    if str(message.chat.id) == TELEGRAM_CHAT_ID:
        bot.reply_to(message, "🔁 Refreshing token...")
        success = refresh_token()
        msg = "✅ Token refreshed!" if success else "❌ Failed to refresh token."
        bot.send_message(message.chat.id, msg)
    else:
        bot.reply_to(message, "⛔ Unauthorized user.")

@bot.message_handler(commands=["start"])
def start_msg(message):
    bot.reply_to(message, "👋 Use /refresh to refresh Fyers token manually.")

print("🚀 Token bot running...")
if __name__ == "__main__":
    IS_GITHUB = os.getenv("GITHUB_ACTIONS", "") == "true"

    if IS_GITHUB:
        print("🔁 Running in GitHub Actions... refreshing token only")
        refresh_token()  # Just refresh once and exit
    else:
        print("🚀 Running locally. Telegram Bot starting...")
        bot.polling()
