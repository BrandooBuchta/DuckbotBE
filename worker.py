import time
import requests

TRACE_API_URL = "https://bot-configurator-api.onrender.com/run-customers-trace"
SEQ_API_URL = "https://bot-configurator-api.onrender.com/run-sequences"

while True:
    try:
        response = requests.post(TRACE_API_URL)
        response = requests.post(SEQ_API_URL)
        print(f"✅ API response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error calling API: {e}")

    time.sleep(60)  # Počkej 60 sekund a zavolej znovu
