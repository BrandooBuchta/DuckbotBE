from sqlalchemy.orm import Session
from models.bot import Bot, Sequence
from schemas.bot import SignUp, SignIn, SignInResponse, BaseBot, UpdateBot, PublicBot, Statistic
from models.user import User
from security import get_password_hash, verify_password
from base64 import b64decode, b64encode
import uuid
from uuid import UUID

def verify_token(db: Session, bot_id: UUID, token: str) -> bool:
    bot, status = get_bot(db, bot_id)
    print("bot_id: ", bot_id, " token: ", token)
    if bot and bot.token == token:
        print("true")
        return True
    return False


def _decode_base64_with_padding(base64_str: str) -> str:
    base64_str = base64_str + "=" * ((4 - len(base64_str) % 4) % 4)
    return b64decode(base64_str).decode()


def get_bot_by_email(db: Session, email: str):
    db_bot = db.query(Bot).filter(Bot.email == email).first()
    if not db_bot:
        return None, 404
    return db_bot, 200


def get_bot(db: Session, bot_id: UUID):
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not db_bot:
        return None, 404
    return db_bot, 200

def get_public_bot(db: Session, bot_id: UUID):
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not db_bot:
        return None, 404
    return PublicBot(
        video_url=bot.video_url,
        bot_url=bot.bot_url,
        is_event=bot.is_event,
        event_capacity=bot.event_capacity,
        event_date=bot.event_date,
        event_location=bot.event_location,
        lang=bot.lang,
    ), 200

def sign_up(db: Session, bot: SignUp):
    decoded_password = _decode_base64_with_padding(bot.password)
    hashed_password = get_password_hash(decoded_password)

    bot_id = uuid.uuid4()

    db_bot = Bot(
        id=bot_id,
        email=bot.email,
        is_event=bot.is_event,
        password=hashed_password,
        devs_currently_assigned=0,
        devs_share=10,

        token=b64encode(bot.token.encode()).decode(),
    )
    db.add(db_bot)
    db.commit()
    db.refresh(db_bot)
    return bot_id, 200

def sign_in(db: Session, sign_in: SignIn):
    db_bot, status_code = get_bot_by_email(db, sign_in.email)
    if not db_bot:
        return None, 404

    decoded_password = _decode_base64_with_padding(sign_in.password)
    status = verify_password(decoded_password, db_bot.password)
    if not status:
        return None, 400

    bot_data = BaseBot(
        id=db_bot.id,
        name=db_bot.name,
        email=db_bot.email,
        video_url=db_bot.video_url,
        support_contact=db_bot.support_contact,
        is_event=db_bot.is_event,
        event_capacity=db_bot.event_capacity,
        event_date=db_bot.event_date,
        event_location=db_bot.event_location,
        lang=db_bot.lang,

    )

    return SignInResponse(token=db_bot.token, bot=bot_data), 200

def update_bot(db: Session, bot_id: UUID, bot: UpdateBot):
    db_bot, status = get_bot(db, bot_id)
    if not db_bot:
        return 404, None
    for key, value in bot.dict(exclude_unset=True).items():
        setattr(db_bot, key, value)
    db.commit()
    db.refresh(db_bot)
    return db_bot, 200

def get_statistics(db: Session, bot_id: UUID):
    users = db.query(User).filter(User.bot_id == bot_id).all()

    level_counts = {0: 0, 1: 0, 2: 0}
    for user in users:
        if user.client_level in level_counts:
            level_counts[user.client_level] += 1

    return [
        Statistic(title="Nezastakováno", value=level_counts[0]),
        Statistic(title="Zastakováno", value=level_counts[1]),
        Statistic(title="Affiliate", value=level_counts[2]),
        Statistic(title="Celkem", value=len(users))
    ]