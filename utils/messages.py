import json
import os

def get_next_message(user_next_message_id: int, level: int):
    SEQUENCES_FILE_PATH = f"data/sequences/level_{level}-dev.json"

    if not os.path.exists(SEQUENCES_FILE_PATH):
        raise FileNotFoundError(f"Soubor {SEQUENCES_FILE_PATH} neexistuje")

    with open(SEQUENCES_FILE_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    next_message = next((msg for msg in data["messages"] if msg["id"] == user_next_message_id), None)

    if not next_message:
        raise ValueError(f"Zpráva s ID {user_next_message_id} nebyla nalezena")

    return next_message