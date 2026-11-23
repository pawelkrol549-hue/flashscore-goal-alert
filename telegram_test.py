
import os
import requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

message = """
🟢 TEST SYSTEMU GOAL ALERT

⚽ Bot Telegram działa poprawnie!

Źródło: Flashscore
Status: Połączenie testowe
"""

response = requests.post(
    url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    },
    timeout=20
)

print(response.status_code)
print(response.json())

response.raise_for_status()
