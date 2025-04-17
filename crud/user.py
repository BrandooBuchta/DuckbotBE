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

def update_users_position(db: Session, user_id: UUID, next_message_id: str, next_message_send_after: Optional[int] = None):
    now = datetime.now()

    db_user = db.query(User).filter(User.id == user_id).first()

    if db_user:
        db_user.next_message_id = next_message_id
        if next_message_id == 1:
            db.commit()
            db.refresh(db_user)
            return db_user

        if next_message_send_after:
            logger.info("next_message_send_after exists")
            db_user.send_message_at = now + timedelta(minutes=next_message_send_after)
        else:
            logger.info("next_message_send_after ain't exists")
            db_user.send_message_at = None
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

from datetime import datetime, timedelta, timezone
import requests
from base64 import b64decode

def send_message_to_user(db: Session, user: UserBase):
    logger.debug(f"Preparing to send message to user: {user.chat_id}")
    bot, status = get_bot(db, user.bot_id)
    if status != 200:
        logger.error(f"Failed to get bot data, status: {status}")
        return

    telegram_api_url = f"https://api.telegram.org/bot{b64decode(bot.token).decode()}"
    url = f"{telegram_api_url}/sendMessage"
    logger.debug(f"Telegram API URL: {url}")

    messages = get_messages(user.client_level, bot.lang, bot.is_event, user.bot_id)
    message = next((e for e in messages if e["id"] == user.next_message_id), None)

    if message is None:
        logger.warning(f"⚠️ No message found for user {user.chat_id}. Skipping.")
        return

    logger.debug(f"Message content: {message}")
        
    should_send = False
    now = datetime.now(timezone.utc)

    if user.send_message_at is None:
        logger.info(f"send_message_at is None, sending immediately.")
        should_send = True
    else:
        logger.info(f"send_message_at exists: {user.send_message_at}")
        time_diff = (now - user.send_message_at).total_seconds()
        
        if time_diff < 0:
            logger.info(f"❌ Zpráva je naplánovaná na budoucnost. Nebudu ji posílat.")
            should_send = False
        elif time_diff > 900:  # 900 sekund = 15 minut
            logger.info(f"❌ Zpráva je starší než 15 minut ({time_diff:.2f} s). Přeskakuji odeslání.")
            should_send = False
        else:
            logger.info(f"✅ Čas je správný, odesílám zprávu.")
            should_send = True

    data = {
        "chat_id": user.chat_id,
        "text": replace_variables(db, user.bot_id, user.chat_id, message["content"]),
        "parse_mode": "html"
    }
    logger.debug(f"Message payload: {data}")

    if message.get("level_up_question"):  
        data["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "ANO", "callback_data": f"{user.id}|t"},
                {"text": "NE", "callback_data": f"{user.id}|f"},
            ]]
        }
        logger.debug("Added level-up question buttons.")

    print ("should_send before sending", should_send)
    if should_send:
        logger.info("Sending message...")
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            logger.info(f"Message sent successfully to {user.chat_id}")
        except requests.RequestException as e:
            logger.error(f"Failed to send message: {e}")
            return
    else:
        logger.info("Message was not sent due to conditions not being met.")

    update_users_position(db, user.id, message["next_message_id"], message.get("next_message_send_after"))