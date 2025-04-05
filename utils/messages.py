import json
import os
from uuid import UUID

def get_messages(level: int, lang: str, is_event: bool, bot_id: UUID):
    event_path = "event/" if is_event else "online/"

    custom_path = f"data/customs/{bot_id}/level-{level}.json"
    sequences_path = f"data/traces/{lang}/{event_path}level-{level}.json"

    if os.path.exists(custom_path):
        path = custom_path
    elif os.path.exists(sequences_path):
        path = sequences_path
    else:
        raise FileNotFoundError(f"Nenalezen ani {custom_path}, ani {sequences_path}")

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data.get("messages", [])
