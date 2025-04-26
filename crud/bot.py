from sqlalchemy.orm import Session
from models.bot import Bot, Sequence, AnalyticData
from schemas.bot import SignUp, SignIn, SignInResponse, BaseBot, UpdateBot, PublicBot, Statistic
from models.user import User
from security import get_password_hash, verify_password
from base64 import b64decode, b64encode
import uuid
from uuid import UUID
import requests
from sqlalchemy import or_

def verify_token(db: Session, bot_id: UUID, token: str) -> bool:
    bot, status = get_bot(db, bot_id)
    if bot and bot.token == token:
        return True
    return False


def _decode_base64_with_padding(base64_str: str) -> str:
    base64_str = base64_str + "=" * ((4 - len(base64_str) % 4) % 4)
    return b64decode(base64_str).decode()


def get_bot_by_name(db: Session, name: str):
    db_bot = db.query(Bot).filter(
        or_(
            Bot.name == name,
            Bot.event_name == name
        )
    ).first()
    if not db_bot:
        return None, 404
    return db_bot, 200


def get_bot(db: Session, bot_id: UUID):
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not db_bot:
        return None, 404
    return db_bot, 200

def get_public_bot(db: Session, name: str):
    db_bot = db.query(Bot).filter(
        or_(
            Bot.name == name,
            Bot.event_name == name
        )
    ).first()

    if not db_bot:
        return None, 404

    return PublicBot(
        video_url=db_bot.video_url,
        bot_url=db_bot.bot_url,
        is_event=db_bot.is_event,
        event_capacity=db_bot.event_capacity,
        event_date=db_bot.event_date,
        event_location=db_bot.event_location,
        event_name=db_bot.event_name,
        lang=db_bot.lang,
    ), 200

def sign_up(db: Session, bot: SignUp):
    decoded_password = _decode_base64_with_padding(bot.password)
    hashed_password = get_password_hash(decoded_password)

    bot_id = uuid.uuid4()

    telegram_api_url = f"https://api.telegram.org/bot{bot.token}/getMe"
    response = requests.get(telegram_api_url)

    bot_url = None
    if response.status_code == 200:
        data = response.json()
        if data.get("ok"):
            username = data["result"].get("username")
            if username:
                bot_url = f"https://t.me/{username}"


    db_bot = Bot(
        id=bot_id,
        name=bot.name,
        event_name=bot.event_name,
        is_event=bot.is_event,
        password=hashed_password,
        bot_url=bot_url,

        token=b64encode(bot.token.encode()).decode(),
    )
    db.add(db_bot)
    db.commit()
    db.refresh(db_bot)
    return bot_id, 200

def sign_in(db: Session, sign_in: SignIn):
    db_bot, status_code = get_bot_by_name(db, sign_in.name)
    if not db_bot:
        return None, 404

    decoded_password = _decode_base64_with_padding(sign_in.password)
    status = verify_password(decoded_password, db_bot.password)
    if not status:
        return None, 400

    bot_data = BaseBot(
        id=db_bot.id,
        name=db_bot.name,
        video_url=db_bot.video_url,
        support_contact=db_bot.support_contact,
        is_event=db_bot.is_event,
        event_capacity=db_bot.event_capacity,
        event_date=db_bot.event_date,
        event_location=db_bot.event_location,
        event_name=db_bot.event_name,
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

def increase_analytic_data(db: Session, bot_name: UUID):
    db_bot, status = get_bot_by_name(db, bot_name)

    db_data = AnalyticData(
        bot_id=db_bot.id,
        id=uuid.uuid4()
    )
    db.add(db_data)
    db.commit()
    db.refresh(db_data)

    return db_data, 200

def get_statistics(db: Session, bot_id: UUID):
    db_analytics_data = db.query(AnalyticData).filter(AnalyticData.bot_id == bot_id).all()
    users = db.query(User).filter(User.bot_id == bot_id).all()

    level_counts = {0: 0, 1: 0, 2: 0}
    for user in users:
        if user.client_level in level_counts:
            level_counts[user.client_level] += 1

    conversion_page_bot = (len(users) / len(db_analytics_data) * 100) if len(db_analytics_data) > 0 else 0
    conversion_bot_staked = (len(users) / level_counts[1] * 100) if level_counts[1] > 0 else 0

    return [
        Statistic(title="Návštěvníci webu", value=len(db_analytics_data)),
        Statistic(title="Nezastakováno", value=level_counts[0]),
        Statistic(title="Zastakováno", value=level_counts[1]),
        Statistic(title="Affiliate", value=level_counts[2]),
        Statistic(title="Celkem v Botovi", value=len(users)),
        Statistic(title="Konverzní poměr (Stránka/Bot)", value=conversion_page_bot),
        Statistic(title="Konverzní poměr (Bot/Staked)", value=conversion_bot_staked),
    ]