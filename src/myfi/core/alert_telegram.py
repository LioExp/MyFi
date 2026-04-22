import sys
import requests
from config.config import TOKEN, CHAT_ID



def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown" # Optional: allows bold/italic text
    }
    
    response = requests.post(url, data=payload)
    return response.json()


if __name__ == '__main__':
    MESSAGE = "Hello from Python!"
    result = send_telegram_message(TOKEN, CHAT_ID, MESSAGE)
    print(result)
