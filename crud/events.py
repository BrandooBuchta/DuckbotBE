from datetime import datetime
from typing import Optional
import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_event_date(event_name: str) -> Optional[datetime]:
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

    url = "https://lewolqdkbulwiicqkqnk.supabase.co/rest/v1/events?select=*&order=timestamp.asc"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logger.error(f"Failed to fetch events: {response.status_code} {response.text}")
        return None

    events = response.json()
    now_timestamp = datetime.utcnow().timestamp()

    # Filtrujeme eventy podle názvu a hledáme nejbližší budoucí
    future_events = [
        event for event in events
        if event_name.lower() in event.get("title", {}).get("en", "").lower()
        and event.get("timestamp") > now_timestamp
    ]

    if not future_events:
        logger.warning(f"No upcoming event found for {event_name}.")
        return None

    # Seřadíme podle timestampu a vezmeme nejbližší
    next_event = sorted(future_events, key=lambda e: e["timestamp"])[0]
    next_event_date = datetime.utcfromtimestamp(next_event["timestamp"])

    logger.info(f"Next event for {event_name}: {next_event_date}")
    return next_event_date
