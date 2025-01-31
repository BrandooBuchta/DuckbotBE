# crud/user.py

from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserCreate
from uuid import UUID, uuid4

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
            is_client=user.is_client,
            academy_link=None,
            name=None
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

def update_users_academy_link(db: Session, user_id: UUID, academy_link: str):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.academy_link = academy_link
        db.commit()
        db.refresh(db_user)
    return db_user

def get_all_users(db: Session, bot_id: UUID):
    return db.query(User).filter(User.bot_id == bot_id).all()

def get_audience(db: Session, bot_id: UUID, for_client: bool, for_new_client: bool):
    if for_client and for_new_client:
        return db.query(User).filter(User.bot_id == bot_id).all()
    if for_client and not for_new_client:
        return db.query(User).filter(User.bot_id == bot_id, User.is_client == True).all()
    if not for_client and for_new_client:
        return db.query(User).filter(User.bot_id == bot_id, User.is_client == False).all()
    if not for_client and not for_new_client:
        return []

def get_user_by_id(db: Session, user_id: UUID):
    return db.query(User).filter(User.id == user_id).first()

def get_current_user(db: Session, chat_id: int, bot_id: UUID):
    return db.query(User).filter(User.chat_id == chat_id, User.bot_id == bot_id).first()
    