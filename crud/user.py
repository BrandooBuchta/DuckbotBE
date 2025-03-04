# crud/user.py

from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserCreate
from uuid import UUID, uuid4
from typing import List
from datetime import datetime, timedelta

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
        client_level=user.client_level,
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

def update_users_position(db: Session, user_id: UUID, next_message_send_after: int, next_message_id: str):
    now = datetime.now()

    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.message_id = next_message_id
        db_user.send_message_at = now + timedelta(minutes=next_message_send_after)

        db.commit()
        db.refresh(db_user)
    return db_user

def update_users_level(db: Session, user_id: UUID, level: int):
    now = datetime.now()

    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.client_level = level
        db_user.message_id = 0
        db_user.send_message_at = now

        db.commit()
        db.refresh(db_user)
    return db_user