from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserCreate

def create_or_update_user(db: Session, user: UserCreate):
    db_user = db.query(User).filter(User.id == user.id).first()
    if db_user:
        db_user.chat_id = user.chat_id
        if user.name is not None:
            db_user.name = user.name
    else:
        db_user = User(
            id=user.id, 
            chat_id=user.chat_id, 
            is_in_betfin=user.is_in_betfin,
            name=user.name
        )
        db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_name(db: Session, user_id: int, name: str):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.name = name
        db.commit()
        db.refresh(db_user)
    return db_user

def get_all_users(db: Session):
    return db.query(User).all()

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()
