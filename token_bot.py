import os, json, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from fyers_apiv3.accessToken import SessionModel
#from fyers_apiv3.FyersWeb import accessToken  # ✅ Correct import for v3+
import telebot

# --- Load secrets from environment ---
APP_ID = os.getenv("FYERS_APP_ID")
APP_SECRET = os.getenv("FYERS_APP_SECRET")
REDIRECT_URI = os.getenv("FYERS_REDIRECT_URI")
USERNAME = os.getenv("FYERS_USERNAME")
PASSWORD = os.getenv("FYERS_PASSWORD")
PIN = os.getenv("FYERS_PIN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SESSION_PATH = "access_token.json"

# --- Token Generator ---
def refresh_token():
    try:
        print("🔄 Starting token refresh...")
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

        current_url = driver.current_url
        if "auth_code=" not in current_url:
            raise Exception("❌ Auth code not found. Login flow failed.")
        auth_code = current_url.split("auth_code=")[-1]
        print("✅ Auth code received:", auth_code)

        session = accessToken.SessionModel(
            client_id=APP_ID,
            secret_key=APP_SECRET,
            redirect_uri=REDIRECT_URI,
            response_type="code",
            grant_type="authorization_code"
        )
        session.set_token(auth_code)
        response = session.generate_token()
        print("✅ Token response:", response)

        access_token = response["access_token"]
        with open(SESSION_PATH, "w") as f:
            json.dump({"app_id": APP_ID, "access_token": access_token}, f)

        print("✅ Access token saved to", SESSION_PATH)
        return True, response
    except Exception as e:
        print("❌ Error refreshing token:", e)
        return False, str(e)
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
        bot.reply_to(message, "🔄 Refreshing token now...")
        success, result = refresh_token()
        if success:
            bot.send_message(message.chat.id, "✅ Token refreshed!\n\n🔐 Access Token:\n" + result["access_token"][:50] + "...")
        else:
            bot.send_message(message.chat.id, f"❌ Failed to refresh token:\n{result}")
    else:
        bot.reply_to(message, "⛔ Unauthorized user.")

@bot.message_handler(commands=['start'])
def welcome_msg(message):
    bot.send_message(message.chat.id, "👋 Welcome to the Fyers Token Bot!\nUse /refresh to regenerate your token.\n⏰ Auto-refresh is enabled via GitHub Actions at 8 AM IST daily.")

# --- Run bot ---
print("🚀 Telegram Token Bot is running...")
bot.polling()
