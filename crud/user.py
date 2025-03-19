# crud/user.py

from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserCreate, UserBase
from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime, timedelta
from crud.bot import get_bot
from base64 import b64decode
from utils.messages import get_messages
from crud.vars import replace_variables
from crud.events import get_event_date
import requests
import logging

logger = logging.getLogger(__name__)

def get_next_weekday_at(weekday: int, hour: int):
    now = datetime.utcnow()
    days_until_target = (weekday - now.weekday()) % 7

    if days_until_target == 0 and now.hour >= hour:
        days_until_target = 7

    target_day = now + timedelta(days=days_until_target)
    return target_day.replace(hour=hour, minute=0, second=0, microsecond=0)

def get_next_friday_or_monday_at(hour: int):
    now = datetime.utcnow()
    if now.weekday() in [4, 5]:
        return get_next_weekday_at(0, hour)
    return get_next_weekday_at(4, hour)
     
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    try:
        now = datetime.utcnow()
        users = db.query(User).filter(User.send_message_at <= now).limit(100).all()
        
        return users
    finally:
        db.close()

def get_next_msessage_sent_at_by_id(message_id: str, level: str, bot_id: UUID):
    if level == 0:
        match message_id:
            case 4:
                # event_date = get_event_date("Opportunity Call")
                # return (event_date if event_date else get_next_weekday_at(6, 18)) - timedelta(hours=9)
                logger.info("assigning")
                return datetime.now() + timedelta(minutes=1)
            case _:
                # bot, status = get_bot(db, bot_id)
                # new_date = bot.event_date - timedelta(days=1)
                # new_date = new_date.replace(hour=12, minute=0, second=0, microsecond=0)
                # return new_date
                return datetime.now() + timedelta(minutes=1)
    else:
        match message_id:
            case 1:
                # event_date = get_event_date("Launch for Beginners")
                # return (event_date if event_date else get_next_friday_or_monday_at(20)) - timedelta(hours=9)
                return datetime.now() + timedelta(minutes=1)
            case 2:
                # event_date = get_event_date("Základy a bezpečnost kryptoměn")
                # return (event_date if event_date else get_next_weekday_at(2, 20)) - timedelta(hours=9)
                return datetime.now() + timedelta(minutes=1)
            case 3:
                # event_date = get_event_date("Build Your Business")
                # return (event_date if event_date else get_next_weekday_at(3, 20)) - timedelta(hours=9)
                return datetime.now() + timedelta(minutes=1)

def update_users_position(db: Session, user_id: UUID, next_message_id: str, next_message_send_after: Optional[int] = None):
    now = datetime.now()

    db_user = db.query(User).filter(User.id == user_id).first()

    if db_user:
        db_user.next_message_id = next_message_id
        if next_message_send_after:
            logger.info("next_message_send_after exists")
            db_user.send_message_at = now + timedelta(minutes=next_message_send_after)
        else:
            logger.info("no next_message_send_after doesn't exists")
            db_user.send_message_at = get_next_msessage_sent_at_by_id(next_message_id, db_user.client_level, db_user.bot_id)

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
    bot, status = get_bot(db, user.bot_id)
    if status != 200:
        return

    telegram_api_url = f"https://api.telegram.org/bot{b64decode(bot.token).decode()}"
    url = f"{telegram_api_url}/sendMessage"

    messages = get_messages(user.client_level, bot.lang, bot.is_event)
    message = next((e for e in messages if e["id"] == user.next_message_id), None)

    if message is None:
        logger.warning(f"⚠️ Žádná zpráva nenalezena pro uživatele {user.chat_id}. Přeskakuji.")
        return

    if user.send_message_at:
        now = datetime.utcnow()
        send_time = user.send_message_at
        if isinstance(send_time, str):
            send_time = datetime.fromisoformat(send_time)

        if now - send_time > timedelta(minutes=15):
            logger.info(f"📌 Zpráva pro uživatele {user.chat_id} se neodeslala, protože send_message_at je starší než 5 minut.")
            update_users_position(db, user.id, message["next_message_id"], message.get("next_message_send_after"))
            return

    data = {
        "chat_id": user.chat_id,
        "text": replace_variables(db, user.bot_id, user.chat_id, message["content"]),
        "parse_mode": "html"
    }

    if message.get("level_up_question"):  
        data["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "ANO", "callback_data": f"{user.id}|t"},
                {"text": "NE", "callback_data": f"{user.id}|f"},
            ]]
        }

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
    except requests.RequestException as e:
        return

    update_users_position(db, user.id, message["next_message_id"], message.get("next_message_send_after"))
