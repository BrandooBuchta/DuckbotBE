# crud/user.py

from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from models.user import User, Target
from schemas.user import UserCreate, UserBase, UsersReference, PublicUser, TargetCreate, TargetUpdate
from uuid import UUID, uuid4
from typing import List, Optional, Literal, Tuple, Dict, Any
from datetime import datetime, timedelta, timezone
from crud.bot import get_bot
from base64 import b64decode
from utils.messages import get_messages
from crud.vars import replace_variables
import requests
import logging
from math import ceil

logger = logging.getLogger(__name__)

YES_NO_LOCALIZED = {
    "cs": ("ANO", "NE"),
    "sk": ("ÁNO", "NIE"),
    "en": ("YES", "NO"),
    "esp": ("SÍ", "NO"),
}

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
        name=user.name[0].upper() + user.name[1:] if user.name else None,
        username=user.username,
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

def get_all_public_users(
    db: Session,
    bot_id: UUID,
    page: int = 1,
    per_page: int = 20,
    sort_by: Literal["name", "created_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    levels: Optional[List[int]] = None
) -> Dict[str, Any]:
    sort_column = User.created_at if sort_by == "created_at" else User.name
    order_func = asc if sort_order == "asc" else desc

    query = db.query(User).filter(User.bot_id == bot_id)

    if levels:
        query = query.filter(User.client_level.in_(levels))

    total = query.count()
    total_pages = ceil(total / per_page) if per_page else 1

    users = query.order_by(order_func(sort_column)).offset((page - 1) * per_page).limit(per_page).all()

    items = [
        PublicUser(
            id=user.id,
            client_level=user.client_level,
            reference=user.reference,
            rating=user.rating,
            academy_link=user.academy_link,
            name=user.name,
            username=user.username,
            created_at=user.created_at,
        )
        for user in users
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }

def get_audience(db: Session, bot_id: UUID, audience: List[int]):
    return db.query(User).filter(User.bot_id == bot_id, User.client_level.in_(audience)).all()

def get_current_user(db: Session, chat_id: int, bot_id: UUID):
    return db.query(User).filter(User.chat_id == chat_id, User.bot_id == bot_id).first()
    
def get_user(db: Session, user_id: UUID):
    return db.query(User).filter(User.id == user_id).first()

def delete_users(db: Session, user_ids: List[UUID]) -> int:
    deleted_count = db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()
    return deleted_count

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
        if next_message_id == 1 and db_user.client_level == 0:
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

def save_users_level(db: Session, user_id: UUID):
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

def update_rating(db: Session, user_id: UUID, value: int):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.rating = value
        
        db.commit()
        db.refresh(db_user)

    send_message_to_user(db, db_user)
    return db_user

def update_rating(db: Session, user_id: UUID, rating: int):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.rating = rating
        db.commit()
        db.refresh(db_user)

    return db_user

def update_reference(db: Session, user_id: UUID, reference: str):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.reference = reference
        db.commit()
        db.refresh(db_user)

    return db_user

def get_references(db: Session, all_references: bool = False):
    query = db.query(User).filter(User.rating > 4).order_by(User.rating.desc())

    if not all_references:
        query = query.limit(10)

    users = query.all()
    references = [UsersReference(
        name=user.name,
        content=user.reference,
        created_at=user.created_at,
        rating=user.rating,
    ) for user in users if user.reference]

    return references


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
        yes_text, no_text = YES_NO_LOCALIZED.get(bot.lang, ("YES", "NO"))
        data["reply_markup"] = {
            "inline_keyboard": [[
                {"text": yes_text, "callback_data": f"{user.id}|t"},
                {"text": no_text, "callback_data": f"{user.id}|f"},
            ]]
        }

    if message.get("rating_question"):
        data["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "🙁", "callback_data": f"{user.id}|1"},
                {"text": "😕", "callback_data": f"{user.id}|2"},
                {"text": "🙂", "callback_data": f"{user.id}|3"},
                {"text": "😄", "callback_data": f"{user.id}|4"},
                {"text": "🤩", "callback_data": f"{user.id}|5"},
            ]]
        }
        
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

    logger.info(f"this is next_message_send_after and next_message_id: {message.get('next_message_send_after')}, {message['next_message_id']}")

    update_users_position(db, user.id, message["next_message_id"], message.get("next_message_send_after"))

    
def create_target(db: Session, data: TargetCreate):
    user = get_user(db, user_id)
    bot, status = get_bot(db, user_id)
    if not user:
        return None, 404

    target = Target(
        user_id=user.id,
        bot_id=user.bot_id,
        lang=bot.lang,  # nebo jiný fallback
        initial_investment=data.initial_investment,
        monthly_addition=data.monthly_addition,
        duration=data.duration,
        currency=data.currency,
        is_dynamic=data.is_dynamic,
        quantity_affiliate_target=data.quantity_affiliate_target,
        quality_affiliate_target=data.quality_affiliate_target,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target, 201

def update_target(db: Session, user_id: UUID, data: dict):
    target = db.query(Target).filter(Target.user_id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    for key, value in data.items():
        if hasattr(target, key):
            setattr(target, key, value)

    db.commit()
    db.refresh(target)
    return target, 200

def get_target(db: Session, user_id: int):
    target = db.query(Target).filter(Target.user_id == user_id).first()
    if not target:
        return None, 404
    return target, 200