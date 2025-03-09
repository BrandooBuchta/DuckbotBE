from datetime import datetime

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
    
    for event in events:
        if event_name.lower() in event.get("title", {}).get("en", "").lower():
            event_timestamp = event.get("timestamp")
            try:
                parsed_date = datetime.strptime(event_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
                logger.info(f"Found event {event_name}: {parsed_date}")
                return parsed_date
            except ValueError as e:
                logger.error(f"Failed to parse event date: {event_timestamp} - {e}")
                return None
    
    logger.warning(f"Event {event_name} not found.")
    return None
