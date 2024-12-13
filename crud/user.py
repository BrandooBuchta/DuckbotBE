from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate

def create_or_update_user(db: Session, user: UserCreate):
    db_user = db.query(User).filter(User.id == user.id).first()
    if db_user:
        db_user.chat_id = user.chat_id
    else:
        db_user = User(id=user.id, chat_id=user.chat_id, is_in_betfin=user.is_in_betfin)
        db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
