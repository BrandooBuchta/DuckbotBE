from sqlalchemy.orm import Session
from uuid import UUID
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

# getting correct events by lang 
def replace_variables(db: Session, bot_id: UUID, chat_id: UUID, message: str):
    bot, status = get_bot(db, bot_id)
    user = db.query(User).filter(User.chat_id == chat_id, User.bot_id == bot_id).first()

    if not user:
        print(f"User not found for chat_id: {chat_id}, bot_id: {bot_id}")

    name = get_user_name(user.name) if bot.lang in ("cs", "sk") else user.name
    capitalized_name = name[0].upper() + name[1:] if name else None

    variables = [
        {"key": "name", "value": capitalized_name if user and user.name else "uživateli"},
        {"key": "botName", "value": bot.name if bot and bot.name else "tvůj bot"},
        {"key": "supportContact", "value": bot.support_contact if bot and bot.support_contact else "podpora"},
        {"key": "network", "value": "https://discord.gg/U5NtgQjg53"},
        {"key": "eventName", "value": bot.event_name},
        {"key": "eventDate", "value": bot.event_date.strftime("%d. %m. %Y, %H:%M") if bot and bot.event_date else "Datum nenalezeno"},
        {"key": "eventLocation", "value": bot.event_location},
        {"key": "academyLink", "value": user.academy_link},
        {"key": "videoLink", "value": f"https://ducknation.vercel.app/video?lang={bot.lang}&id={user.id}"},
        {"key": "userId", "value": user.id},
    ]

    for var in variables:
        message = message.replace(f"{{{var['key']}}}", str(var["value"]) if var["value"] is not None else "neznámá hodnota")

    return message.replace("<br>", "\n")

def create_event_string(message: str, time: str, url: str):
    variables = [
        {"key": "date", "value": date},
        {"key": "url", "value": url},
    ]

    for var in variables:
        message = message.replace(f"{{{var['key']}}}", str(var["value"]) if var["value"] is not None else "neznámá hodnota")
