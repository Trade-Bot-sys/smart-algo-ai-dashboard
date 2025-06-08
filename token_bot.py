import os
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import telebot
#from fyers_apiv3.FyersWeb import accessToken  # ✅ For fyers-apiv3>=3.0

# --- Load from environment ---
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
        # options.add_argument("--headless")  # Enable for full automation
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/99.0 Safari/537.36")
        options.add_argument("--disable-blink-features=AutomationControlled")

# ✅ Add this line to avoid profile conflicts
        options.add_argument(f"--user-data-dir=/tmp/chrome-user-data-{int(time.time())}")
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 20)

        print("🌐 Navigating to Fyers auth page...")
        driver.get(auth_url)
        print("🌐 Page source preview:")
        print(driver.page_source[:500])  # ✅ Useful debug output

        print("📝 Entering username...")
        wait.until(EC.visibility_of_element_located((By.ID, "fy_username"))).send_keys(USERNAME)
        wait.until(EC.element_to_be_clickable((By.ID, "loginSubmit"))).click()
        driver.save_screenshot("step2_username.png")

        print("🔐 Entering password...")
        wait.until(EC.presence_of_element_located((By.ID, "fy_password"))).send_keys(PASSWORD)
        wait.until(EC.element_to_be_clickable((By.ID, "loginSubmit"))).click()
        driver.save_screenshot("step3_password.png")

        print("🔢 Entering PIN...")
        for i, d in enumerate(PIN, 1):
            wait.until(EC.presence_of_element_located((By.ID, f"pin{i}"))).send_keys(d)
        wait.until(EC.element_to_be_clickable((By.ID, "loginSubmit"))).click()
        driver.save_screenshot("step4_pin.png")

        print("📦 Checking for auth code in URL...")
        time.sleep(5)
        if "auth_code=" not in driver.current_url:
            driver.save_screenshot("error_no_auth_code.png")
            raise Exception("❌ Auth code not found in URL")

        auth_code = driver.current_url.split("auth_code=")[-1].split("&")[0]
        print("✅ Auth code received:", auth_code[:10], "...")

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
        print("❌ Exception occurred:", e)
        try:
            driver.save_screenshot("token_error.png")
        except:
            pass
        return False

    finally:
        try:
            driver.quit()
        except:
            pass

# --- Telegram Bot Handler ---
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

# --- Main Entry Point ---
print("🚀 Token bot running...")
if __name__ == "__main__":
    IS_GITHUB = os.getenv("GITHUB_ACTIONS", "") == "true"
    if IS_GITHUB:
        print("🔁 Running inside GitHub Actions - single token refresh")
        refresh_token()
    else:
        print("💬 Running locally - Telegram bot active")
        bot.polling()
