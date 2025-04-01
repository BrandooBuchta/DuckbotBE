import json
import os
from uuid import UUID

def get_messages(level: int, lang: str, is_event: bool, bot_id: UUID):
    event_path = "event/" if is_event else "online/"

    CUSTOM_PATH = f"data/customs/{bot_id}/level-{level}.json"

    if not os.path.exists(CUSTOM_PATH):
        raise FileNotFoundError(f"Soubor {CUSTOM_PATH} neexistuje")

    SEQUENCES_FILE_PATH = f"data/traces/{lang}/{event_path}level-{level}.json"

    if not os.path.exists(SEQUENCES_FILE_PATH):
        raise FileNotFoundError(f"Soubor {SEQUENCES_FILE_PATH} neexistuje")

    PATH = CUSTOM_PATH if CUSTOM_PATH else SEQUENCES_FILE_PATH

    with open(PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data.get("messages", [])
