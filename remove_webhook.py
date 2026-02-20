import requests
import time
from config import BOT_TOKEN

# Remove webhook using direct API call
url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
response = requests.get(url)
print(f"Webhook removal response: {response.json()}")

# Check if webhook is gone
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
response = requests.get(url)
print(f"Webhook info: {response.json()}")