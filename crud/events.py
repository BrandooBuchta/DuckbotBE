from typing import Optional
import requests
import os

def get_event_date(event_name: str) -> Optional[str]:
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    
    url = "https://lewolqdkbulwiicqkqnk.supabase.co/rest/v1/events?select=*&order=timestamp.asc"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to fetch events: {response.status_code} {response.text}")
        return None
    
    events = response.json()
    
    for event in events:
        if event_name.lower() in event.get("title", {}).get("en", "").lower():
            return event.get("timestamp")
    
    return None
