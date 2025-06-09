# scheduler.py
import schedule
import subprocess
import time
from datetime import datetime

def run_token_script():
    print(f"[{datetime.now()}] 🔄 Running token generator...")
    result = subprocess.run(["python", "generate_access_token.py"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[{datetime.now()}] ✅ Token refreshed successfully.")
    else:
        print(f"[{datetime.now()}] ❌ Error refreshing token:\n{result.stderr}")

# 🔁 Schedule token generator at 9:10 AM every day
schedule.every().day.at("09:10").do(run_token_script)

print("🕒 Scheduler started. Waiting for 09:10 AM IST...")

# Infinite loop to keep scheduler running
while True:
    schedule.run_pending()
    time.sleep(30)
