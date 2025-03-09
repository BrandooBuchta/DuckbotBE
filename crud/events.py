from datetime import datetime
from typing import Optional
import os
import requests
import logging

logging.basicConfig(level=logging.DEBUG)  # Změněno na DEBUG pro lepší logy
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

    logger.debug(f"Fetched {len(events)} events from API.")

    # Opravená filtrace - bereme i český i anglický název eventu
    future_events = [
        event for event in events
        if (
            event_name.lower() in event.get("title", {}).get("en", "").lower()
            or event_name.lower() in event.get("title", {}).get("cs", "").lower()
        )
        and event.get("timestamp", 0) > now_timestamp  # Zabránění KeyError a chybným timestampům
    ]

    logger.debug(f"Found {len(future_events)} future events for '{event_name}'.")

    if not future_events:
        logger.warning(f"No upcoming event found for {event_name}.")
        return None

    # Seřazení a výběr nejbližšího eventu
    next_event = min(future_events, key=lambda e: e["timestamp"])
    next_event_date = datetime.utcfromtimestamp(next_event["timestamp"])

    logger.info(f"Next event for '{event_name}' found: {next_event_date} (ID: {next_event['id']})")
    return next_event_date
