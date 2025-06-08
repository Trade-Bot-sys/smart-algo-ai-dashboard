import telebot
import subprocess
import schedule
import time
import threading
import os

# Load secrets from environment or hardcode (Replace with Streamlit secrets if needed)
TELEGRAM_TOKEN = "your_telegram_bot_token"
CHAT_ID = "your_telegram_chat_id"  # Must be a string

# Initialize the bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 🟢 /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, (
        "👋 Welcome to Fyers Token Bot!\n"
        "Use /refresh to update your Fyers access token.\n"
        "Automatic refresh runs daily at 8:00 AM."
    ))

# 🔄 /refresh command
@bot.message_handler(commands=['refresh'])
def refresh_token_command(message):
    if str(message.chat.id) != CHAT_ID:
        bot.send_message(message.chat.id, "⛔ Unauthorized user.")
        return

    try:
        subprocess.run(["python3", "generate_token.py"], check=True)
        bot.send_message(message.chat.id, "✅ Token refreshed successfully.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Token refresh failed:\n{e}")

# ⏰ Auto-scheduler to refresh token daily
def scheduled_refresh():
    try:
        subprocess.run(["python3", "generate_token.py"], check=True)
        bot.send_message(CHAT_ID, "🔁 Auto-refreshed Fyers token at 8:00 AM.")
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Auto-refresh failed:\n{e}")

# ⏱️ Setup scheduler
schedule.every().day.at("08:00").do(scheduled_refresh)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start schedule thread
threading.Thread(target=run_schedule, daemon=True).start()

# 🔁 Keep bot running
print("🚀 Telegram Token Bot is running...")
bot.polling()
