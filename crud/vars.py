from sqlalchemy.orm import Session
from uuid import UUID
import requests
from typing import Dict
import os
from crud.bot import get_bot
from vokativ import sex, vokativ
from models.user import User
from datetime import datetime

def get_user_name(n):
    if sex(n) == "w":
        return vokativ(n, woman=True)
    return vokativ(n, woman=False) 

def replace_variables(db: Session, bot_id: UUID, chat_id: UUID, message: str):
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

    bot, status = get_bot(db, bot_id)
    user = db.query(User).filter(User.chat_id == chat_id, User.bot_id == bot_id).first()

    if not user:
        print(f"User not found for chat_id: {chat_id}, bot_id: {bot_id}")

    def get_closest_events() -> Dict[str, Dict[str, str]]:
        url = "https://lewolqdkbulwiicqkqnk.supabase.co/rest/v1/events?select=*&order=timestamp.asc"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"Failed to fetch events: {response.status_code} {response.text}")
            return {
                "launch_for_beginners": {"url": "Žádné události nenalezeny", "date": "Datum nenalezeno"},
                "build_your_business": {"url": "Žádné události nenalezeny", "date": "Datum nenalezeno"},
                "opportunity_call": {"url": "Žádné události nenalezeny", "date": "Datum nenalezeno"},
                "cryptocurrency_basics_and_security": {"url": "Žádné události nenalezeny", "date": "Datum nenalezeno"},
            }

        events = response.json()

        keywords = [
            ("launch_for_beginners", "Launch for Beginners"),
            ("build_your_business", "Build Your Business"),
            ("opportunity_call", "Opportunity Call"),
            ("cryptocurrency_basics_and_security", "Základy a bezpečnost kryptoměn"),
        ]

        closest_events = {key: {"url": "Žádné události nenalezeny", "date": "Datum nenalezeno"} for key, _ in keywords}

        for key, keyword in keywords:
            for event in events:
                if keyword.lower() in event["title"]["en"].lower():
                    timestamp = event["timestamp"]
                    try:
                        # Převedeme datum z ISO na požadovaný formát
                        formatted_date = datetime.fromisoformat(timestamp).strftime("%d. %m. %Y, %H:%M")
                    except Exception as e:
                        print(f"Error parsing date for event: {e}")
                        formatted_date = "Datum nelze načíst"

                    closest_events[key] = {
                        "url": event["url"],
                        "date": formatted_date
                    }
                    break

        return closest_events

    closest_events = get_closest_events()

    name = get_user_name(user.name)
    capitalized_name = name[0].upper() + name[1:] if name else None

    variables = [
        {"key": "name", "value": capitalized_name if user and user.name else "uživateli"},
        {"key": "botName", "value": bot.name if bot and bot.name else "tvůj bot"},
        {"key": "supportContact", "value": bot.support_contact if bot and bot.support_contact else "podpora"},
        {"key": "launchForBeginners", "value": closest_events["launch_for_beginners"]["url"]},
        {"key": "launchForBeginnersDate", "value": closest_events["launch_for_beginners"]["date"]},
        {"key": "buildYourBusiness", "value": closest_events["build_your_business"]["url"]},
        {"key": "buildYourBusinessDate", "value": closest_events["build_your_business"]["date"]},
        {"key": "opportunityCall", "value": closest_events["opportunity_call"]["url"]},
        {"key": "opportunityCallDate", "value": closest_events["opportunity_call"]["date"]},
        {"key": "crypto", "value": closest_events["cryptocurrency_basics_and_security"]["url"]},
        {"key": "cryptoDate", "value": closest_events["cryptocurrency_basics_and_security"]["date"]},
        {"key": "network", "value": "https://discord.gg/U5NtgQjg53"},
        {"key": "eventName", "value": bot.event_name},
        {"key": "eventDate", "value": bot.event_date.strftime("%d. %m. %Y, %H:%M") if bot and bot.event_date else "Datum nenalezeno"},
        {"key": "eventLocation", "value": bot.event_location},
        {"key": "academyLink", "value": user.academy_link}
    ]

    for var in variables:
        message = message.replace(f"{{{var['key']}}}", str(var["value"]) if var["value"] is not None else "neznámá hodnota")

    return message.replace("<br>", "\n")
