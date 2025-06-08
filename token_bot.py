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
        driver = webdriver.Chrome(options=options)

        driver.get(auth_url)
        time.sleep(3)
        driver.find_element(By.ID, "fy_username").send_keys(USERNAME)
        driver.find_element(By.ID, "loginSubmit").click()
        time.sleep(2)
        driver.find_element(By.ID, "fy_password").send_keys(PASSWORD)
        driver.find_element(By.ID, "loginSubmit").click()
        time.sleep(2)
        for i, d in enumerate(PIN, 1):
            driver.find_element(By.ID, f"pin{i}").send_keys(d)
        driver.find_element(By.ID, "loginSubmit").click()
        time.sleep(4)

        current_url = driver.current_url
        if "auth_code=" not in current_url:
            raise Exception("❌ Login failed. Auth code not found.")
        auth_code = current_url.split("auth_code=")[-1].split("&")[0]
        print("✅ Auth code received:", auth_code)

        # Exchange auth code for access token
        token_url = "https://api.fyers.in/api/v2/token"
        payload = {
            "grant_type": "authorization_code",
            "appIdHash": APP_ID,
            "code": auth_code,
            "secretKey": APP_SECRET
        }
        headers = {"content-type": "application/json"}
        response = requests.post(token_url, json=payload, headers=headers)
        response.raise_for_status()
        access_token = response.json().get("access_token")

        if not access_token:
            raise Exception("❌ Failed to get access token.")

        # Save token
        with open(SESSION_PATH, "w") as f:
            json.dump({
                "app_id": APP_ID,
                "access_token": access_token
            }, f)

        print("✅ Token saved successfully!")
        return True

    except Exception as e:
        print("❌ Error:", e)
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
bot.polling()
