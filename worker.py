import time
import requests

API_URL = "https://bot-configurator-api.onrender.com/run-process"

while True:
    try:
        response = requests.post(API_URL)
        print(f"✅ API response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error calling API: {e}")

    time.sleep(60)  # Počkej 60 sekund a zavolej znovu
