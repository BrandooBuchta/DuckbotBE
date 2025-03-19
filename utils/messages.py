import json
import os

def get_messages(level: int, lang: str, is_event: bool):
    SEQUENCES_FILE_PATH = f"data/traces/{lang}/{"event/" if is_event else ""}level-{level}.json"

    if not os.path.exists(SEQUENCES_FILE_PATH):
        raise FileNotFoundError(f"Soubor {SEQUENCES_FILE_PATH} neexistuje")

    with open(SEQUENCES_FILE_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data.get("messages", [])
