from sqlalchemy.orm import Session
from models.bot import Bot
from schemas.bot import SignUp, SignIn
from passlib.context import CryptContext
from security import get_password_hash, verify_password
from base64 import b64decode, b64encode
import uuid

def get_bot_by_name(db: Session, name: str):
    db_bot = db.query(Bot).filter(Bot.name == name).first()
    if not db_bot:
        return None, 404
    return db_bot, 200

def get_bot(db: Session, bot_id: str):
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not db_bot:
        return None, 404
    return db_bot, 200

def sign_up(db: Session, bot: SignUp):
    max_bigint = 9223372036854775807
    id = uuid.uuid4().int % max_bigint

    hashed_password = get_password_hash(b64decode(bot.password).decode())

    db_bot = Bot(
        id=id,
        name=bot.name,
        password=hashed_password,
        token=b64encode(bot.token.encode()).decode(),
    )
    db.add(db_bot)
    db.commit()
    db.refresh(db_bot)
    return 200

def sign_in(db: Session, sign_in: SignIn):
    db_bot, status_code = get_bot_by_name(db, sign_in.name)
    if not db_bot:
        return None, 404

    # Verify password after decoding b64
    status = verify_password(b64decode(sign_in.password).decode(), db_bot.password)
    if not status:
        return None, 400

    # Return the token encrypted with b64
    return db_bot.token, 200

def get_bot(db: Session, bot_id: int):
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not db_bot:
        return None, 404
    return db_bot, 200
