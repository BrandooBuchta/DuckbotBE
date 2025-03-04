from sqlalchemy.orm import Session
from uuid import UUID
import requests
from typing import Dict
import os
from crud.bot import get_bot
from crud.user import get_current_user
from vokativ import sex, vokativ

def get_user_name(n):
    if (sex(n) == "w"):
        return vokativ(n, woman=True)

    return vokativ(n, woman=False) 

def replace_variables(db: Session, bot_id: UUID, chat_id: UUID, message: str):
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    
    bot, status = get_bot(db, bot_id)
    user = get_current_user(db, chat_id, bot_id)

    if not user:
        print(f"User not found for chat_id: {chat_id}, bot_id: {bot_id}")

    def get_closest_events() -> Dict[str, str]:
        url = "https://lewolqdkbulwiicqkqnk.supabase.co/rest/v1/events?select=*&order=timestamp.asc"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
        }

        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Failed to fetch events: {response.status_code} {response.text}")
            return {
                "launch_for_beginners": "Žádné události nenalezeny",
                "build_your_business": "Žádné události nenalezeny",
                "opportunity_call": "Žádné události nenalezeny",
            }

        events = response.json()

        keywords = ["Launch for Beginners", "Build Your Business", "Opportunity Call"]
        closest_events = {
            "launch_for_beginners": "Žádné události nenalezeny",
            "build_your_business": "Žádné události nenalezeny",
            "opportunity_call": "Žádné události nenalezeny",
        }

        for keyword in keywords:
            for event in events:
                if keyword.lower() in event["title"]["en"].lower():
                    key = keyword.lower().replace(" ", "_")
                    closest_events[key] = event["url"]
                    break  # Stop after finding the closest event for this keyword

        return closest_events

    closest_events = get_closest_events()


    name = get_user_name(user.name)
    capitalized_name = name[0].upper() + name[1:] if name else None

    variables = [
        {
            "key": "name",
            "value": capitalized_name if user and user.name else "uživateli"
        },
        {
            "key": "botName",
            "value": bot.name if bot and bot.name else "tvůj bot"
        },
        {
            "key": "supportContact",
            "value": bot.support_contact if bot and bot.support_contact else "podpora"
        },
        {
            "key": "launchForBeginners",
            "value": closest_events["launch_for_beginners"]
        },
        {
            "key": "buildYourBusiness",
            "value": closest_events["build_your_business"]
        },
        {
            "key": "opportunityCall",
            "value": closest_events["opportunity_call"]
        },
        {
            "key": "network",
            "value": "https://discord.gg/U5NtgQjg53"
        },
    ]

    for var in variables:
        message = message.replace(f"{{{var['key']}}}", var["value"] or "neznámá hodnota")

    return message.replace("<br>", "\n")
