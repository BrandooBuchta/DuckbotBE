# crud/user.py

from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserCreate, UserBase
from uuid import UUID, uuid4
from typing import List
from datetime import datetime, timedelta
from crud.bot import get_bot
from base64 import b64decode
from utils.messages import get_messages
from crud.vars import replace_variables
from crud.events import get_event_date
import requests

def create_or_update_user(db: Session, user: UserCreate):
    db_user = db.query(User).filter(User.chat_id == user.chat_id, User.bot_id == user.bot_id).first()
    if db_user:
        db_user.chat_id = user.chat_id
        if user.name is not None:
            db_user.name = user.name
    else:
        db_user = User(

            id=uuid4(), 
            from_id=user.from_id, 
            chat_id=user.chat_id, 
            bot_id=user.bot_id,
            client_level=user.client_level,
            academy_link=None,
            name=None
        )
        db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_user(db: Session, user: UserCreate):
    db_user = User(
        id=uuid4(), 
        from_id=user.from_id, 
        chat_id=user.chat_id, 
        bot_id=user.bot_id,
        client_level=0,    
        send_message_at=None,
        next_message_id=0,
        academy_link=None,
        name=user.name[0].upper() + user.name[1:] if user.name else None
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_name(db: Session, user_id: UUID, name: str):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.name = name
        db.commit()
        db.refresh(db_user)
    return db_user

def update_client_level(db: Session, user_id: UUID, level: int):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.client_level = level
        db.commit()
        db.refresh(db_user)
    return db_user

def update_users_academy_link(db: Session, user_id: UUID, academy_link: str):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.academy_link = academy_link
        db.commit()
        db.refresh(db_user)
    return db_user

def get_all_users(db: Session, bot_id: UUID):
    return db.query(User).filter(User.bot_id == bot_id).all()

def get_audience(db: Session, bot_id: UUID, audience: List[int]):
    return db.query(User).filter(User.bot_id == bot_id, User.client_level.in_(audience)).all()

def get_current_user(db: Session, chat_id: int, bot_id: UUID):
    return db.query(User).filter(User.chat_id == chat_id, User.bot_id == bot_id).first()
    
def get_user(db: Session, user_id: UUID):
    return db.query(User).filter(User.id == user_id).first()

def get_users_in_queue(db: Session):
    return db.query(User).filter(User.send_message_at <= datetime.utcnow()).all()

def get_next_msessage_sent_at_by_id(message_id: str, level: str):
    if level == 0:
        match message_id:
            case 5:
                print ("event_date: ", get_event_date("opportunity_call"))
                return get_event_date("opportunity_call") - timedelta(hours=9)
    else:
        match message_id:
            case 1:
                return get_event_date("launch_for_begginers") - timedelta(hours=9)
            case 2:
                return get_event_date("cryptocurrency_basics_and_security") - timedelta(hours=9)
            case 3:
                return get_event_date("build_your_business") - timedelta(hours=9)

def update_users_position(db: Session, user_id: UUID, next_message_id: str, next_message_send_after: int):
    now = datetime.now()

    db_user = db.query(User).filter(User.id == user_id).first()

    if db_user:
        db_user.next_message_id = next_message_id
        if next_message_send_after:
            print("next_message_send_after is none")
            db_user.send_message_at = now + timedelta(minutes=next_message_send_after)
        else:
            print("no next_message_send_after is not none")
            db_user.send_message_at = get_next_msessage_sent_at_by_id(next_message_id, db_user.client_level)

        db.commit()
        db.refresh(db_user)
    return db_user

def update_users_level(db: Session, user_id: UUID):
    now = datetime.now()

    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user.client_level == 2:
        return 

    if db_user:
        db_user.client_level = db_user.client_level + 1
        db_user.next_message_id = 0
        db_user.send_message_at = now

        db.commit()
        db.refresh(db_user)

    send_message_to_user(db, db_user)
    return db_user

def send_message_to_user(db: Session, user: UserBase):
    print(f"Starting sending message for user {user.chat_id}\n")

    bot, status = get_bot(db, user.bot_id)
    telegram_api_url = f"https://api.telegram.org/bot{b64decode(bot.token).decode()}"
    url = f"{telegram_api_url}/sendMessage"

    messages = get_messages(user.client_level)
    message = next((e for e in messages if e["id"] == user.next_message_id), None)

    if message is None:
        print(f"No message found for user {user.chat_id}.")
        return

    print(f"Message found: {message}")

    data = {
        "chat_id": user.chat_id,
        "text": replace_variables(db, user.bot_id, user.chat_id, message["content"]),
        "parse_mode": "html"
    }

    if message.get("level_up_question"):  # Použití .get() zabrání KeyError
        data["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "ANO", "callback_data": f"{user.id}|t"},
                {"text": "NE", "callback_data": f"{user.id}|f"},
            ]]
        }

    print(f"Telegram API URL: {url}")
    print(f"Data being sent: {data}")

    response = requests.post(url, json=data)
    
    print(f"Response status code: {response.status_code}")
    print(f"Response JSON: {response.text}")

    response.raise_for_status()  # Vyvolá výjimku, pokud request selže

    update_users_position(db, user.id, message["next_message_id"], message["next_message_send_after"])
