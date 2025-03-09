from datetime import datetime
from typing import Optional
import os
import requests
import logging

logging.basicConfig(level=logging.DEBUG)  # Debug režim
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
    logger.debug(f"Current timestamp (UTC now): {now_timestamp}")

    logger.debug("Checking event titles in API response:")
    for event in events:
        en_title = event.get("title", {}).get("en", "").strip().lower()
        event_timestamp = event.get("timestamp", 0)
        logger.debug(f"Event ID {event.get('id')}: '{en_title}' (timestamp: {event_timestamp})")

    event_name_lower = event_name.strip().lower()
    logger.debug(f"Looking for event: '{event_name_lower}'")

    future_events = [
        event for event in events
        if event.get("title", {}).get("en", "").strip().lower() == event_name_lower
        and event.get("timestamp", 0) > now_timestamp
    ]

    logger.debug(f"Found {len(future_events)} future events for '{event_name}'.")

    if not future_events:
        logger.warning(f"No upcoming event found for {event_name}.")
        return None

    next_event = min(future_events, key=lambda e: e["timestamp"])
    next_event_date = datetime.utcfromtimestamp(next_event["timestamp"])

    logger.info(f"Next event for '{event_name}' found: {next_event_date} (ID: {next_event['id']})")
    return next_event_date
