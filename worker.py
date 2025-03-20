import time
import requests

TRACE_API_URL = "https://bot-configurator-api.onrender.com/run-customers-trace"
SEQ_API_URL = "https://bot-configurator-api.onrender.com/run-sequences"
SLEEP_INTERVAL = 60  # Bude běžet každou minutu

while True:
    try:
        # Volání API s timeoutem
        trace_response = requests.post(TRACE_API_URL, timeout=30)
        print(f"✅ TRACE API response: {trace_response.status_code} - {trace_response.text}")

        seq_response = requests.post(SEQ_API_URL, timeout=30)
        print(f"✅ SEQ API response: {seq_response.status_code} - {seq_response.text}")

    except requests.exceptions.Timeout:
        print("⏳ Timeout při volání API!")

    except requests.exceptions.RequestException as e:
        print(f"❌ Chyba při volání API: {e}")

    time.sleep(SLEEP_INTERVAL)  # Počkej 60 sekund a zavolej znovu
