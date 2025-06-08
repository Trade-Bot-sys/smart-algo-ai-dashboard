import os, json, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from fyers_apiv3 import accessToken
import telebot

# --- Secrets ---
APP_ID = "YOUR_APP_ID"
APP_SECRET = "YOUR_APP_SECRET"
REDIRECT_URI = "YOUR_REDIRECT_URL"
USERNAME = "YOUR_FYERS_ID"
PASSWORD = "YOUR_FYERS_PASSWORD"
PIN = "YOUR_PIN"
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"
SESSION_PATH = "access_token.json"

# --- Token Generator ---
def refresh_token():
    try:
        auth_url = f"https://api.fyers.in/api/v2/generate-authcode?client_id={APP_ID}&redirect_uri={REDIRECT_URI}&response_type=code&state=state123"
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)

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

        auth_code = driver.current_url.split("auth_code=")[-1]

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

        print("✅ Token refreshed.")
        return True
    except Exception as e:
        print("❌ Error refreshing token:", e)
        return False
    finally:
        try:
            driver.quit()
        except:
            pass

# --- Telegram Bot ---
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['refresh'])
def handle_refresh(message):
    if str(message.chat.id) == TELEGRAM_CHAT_ID:
        success = refresh_token()
        bot.reply_to(message, "✅ Token refreshed!" if success else "❌ Failed to refresh token.")
    else:
        bot.reply_to(message, "❌ Unauthorized user.")

# --- Manual Run or Background ---
if __name__ == "__main__":
    # You can run it manually:
    # refresh_token()
    
    # Or keep telegram bot polling
    bot.polling()
