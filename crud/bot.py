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
from datetime import datetime, timedelta
from typing import Optional, Tuple

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

def get_statistics(
    db: Session,
    bot_id: UUID,
    interval: str = "total",
    custom_range: Optional[Tuple[datetime, datetime]] = None
):
    now = datetime.utcnow()

    def get_range(interval: str, custom: Optional[Tuple[datetime, datetime]]):
        if interval == "lastHour":
            end = now
            start = now - timedelta(hours=1)
        elif interval == "lastDay":
            end = now
            start = now - timedelta(days=1)
        elif interval == "lastWeek":
            end = now
            start = now - timedelta(weeks=1)
        elif interval == "lastMonth":
            end = now
            start = now - timedelta(days=30)
        elif interval == "lastYear":
            end = now
            start = now - timedelta(days=365)
        elif interval == "custom" and custom:
            start, end = custom
        else:
            return None, None
        return start, end

    def get_previous_range(start: datetime, end: datetime) -> Tuple[datetime, datetime]:
        delta = end - start
        return start - delta, start

    start, end = get_range(interval, custom_range)
    prev_start, prev_end = get_previous_range(start, end) if start and end else (None, None)

    analytics_query = db.query(AnalyticData).filter(AnalyticData.bot_id == bot_id)
    users_query = db.query(User).filter(User.bot_id == bot_id)

    if start:
        analytics_query = analytics_query.filter(AnalyticData.created_at >= start)
        users_query = users_query.filter(User.created_at >= start)
    if end:
        analytics_query = analytics_query.filter(AnalyticData.created_at <= end)
        users_query = users_query.filter(User.created_at <= end)

    analytics_now = analytics_query.count()
    users_now = users_query.all()

    # Previous analytics
    analytics_prev = 0
    users_prev = []

    if prev_start and prev_end:
        analytics_prev = db.query(AnalyticData).filter(
            AnalyticData.bot_id == bot_id,
            AnalyticData.created_at >= prev_start,
            AnalyticData.created_at <= prev_end
        ).count()

        users_prev = db.query(User).filter(
            User.bot_id == bot_id,
            User.created_at >= prev_start,
            User.created_at <= prev_end
        ).all()

    def calc_change(now_val: int, prev_val: int) -> float:
        if prev_val == 0:
            return 100.0 if now_val > 0 else 0.0
        return round(((now_val - prev_val) / prev_val) * 100, 2)

    level_counts_now = {0: 0, 1: 0, 2: 0}
    for u in users_now:
        if u.client_level in level_counts_now:
            level_counts_now[u.client_level] += 1

    level_counts_prev = {0: 0, 1: 0, 2: 0}
    for u in users_prev:
        if u.client_level in level_counts_prev:
            level_counts_prev[u.client_level] += 1

    conversion_page_bot = (len(users_now) / analytics_now * 100) if analytics_now else 0
    conversion_bot_staked = (len(users_now) / level_counts_now[1] * 100) if level_counts_now[1] else 0

    conversion_page_bot_prev = (len(users_prev) / analytics_prev * 100) if analytics_prev else 0
    conversion_bot_staked_prev = (len(users_prev) / level_counts_prev[1] * 100) if level_counts_prev[1] else 0

    return [
        Statistic(title="Návštěvníci webu", value=analytics_now, change=calc_change(analytics_now, analytics_prev)),
        Statistic(title="Nezastakováno", value=level_counts_now[0], change=calc_change(level_counts_now[0], level_counts_prev[0])),
        Statistic(title="Zastakováno", value=level_counts_now[1], change=calc_change(level_counts_now[1], level_counts_prev[1])),
        Statistic(title="Affiliate", value=level_counts_now[2], change=calc_change(level_counts_now[2], level_counts_prev[2])),
        Statistic(title="Celkem v Botovi", value=len(users_now), change=calc_change(len(users_now), len(users_prev))),
        Statistic(title="Konverzní poměr (Stránka/Bot)", value=conversion_page_bot, is_ratio=True, change=calc_change(conversion_page_bot, conversion_page_bot_prev)),
        Statistic(title="Konverzní poměr (Bot/Staked)", value=conversion_bot_staked, is_ratio=True, change=calc_change(conversion_bot_staked, conversion_bot_staked_prev)),
    ]
