from sqlalchemy.orm import Session
from models.bot import Bot, Sequence, AnalyticData
from schemas.bot import SignUp, SignIn, SignInResponse, BaseBot, UpdateBot, PublicBot, Statistic
from models.user import User
from crud.sequence import create_sequence
from security import get_password_hash, verify_password
from base64 import b64decode, b64encode
import uuid
from uuid import UUID
import requests
from sqlalchemy import or_
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from fastapi import Request

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
        id=db_bot.id,
        video_url=db_bot.video_url,
        videos=db_bot.videos,
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

    create_sequence(db, )
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
) -> List[Statistic]:
    now = datetime.utcnow()

    def get_range(interval: str, custom: Optional[Tuple[datetime, datetime]]) -> Tuple[Optional[datetime], Optional[datetime]]:
        if interval == "lastHour":
            return now - timedelta(hours=1), now
        elif interval == "lastDay":
            return now - timedelta(days=1), now
        elif interval == "lastWeek":
            return now - timedelta(weeks=1), now
        elif interval == "lastMonth":
            return now - timedelta(days=30), now
        elif interval == "lastYear":
            return now - timedelta(days=365), now
        elif interval == "custom" and custom:
            return custom
        return None, None

    def get_previous_range(start: datetime, end: datetime) -> Tuple[datetime, datetime]:
        delta = end - start
        return start - delta, start

    def calc_change(current: int | float, previous: int | float) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 2)

    start, end = get_range(interval, custom_range)
    prev_start, prev_end = get_previous_range(start, end) if start and end else (None, None)

    def get_analytics_count(s: Optional[datetime], e: Optional[datetime]) -> int:
        query = db.query(AnalyticData).filter(AnalyticData.bot_id == bot_id)
        if s: query = query.filter(AnalyticData.created_at >= s)
        if e: query = query.filter(AnalyticData.created_at <= e)
        return query.count()

    def get_users(s: Optional[datetime], e: Optional[datetime]) -> List[User]:
        query = db.query(User).filter(User.bot_id == bot_id)
        if s: query = query.filter(User.created_at >= s)
        if e: query = query.filter(User.created_at <= e)
        return query.all()

    analytics_now = get_analytics_count(start, end)
    analytics_prev = get_analytics_count(prev_start, prev_end)

    users_now = get_users(start, end)
    users_prev = get_users(prev_start, prev_end)

    level_counts_now = {0: 0, 1: 0, 2: 0}
    level_counts_prev = {0: 0, 1: 0, 2: 0}
    for u in users_now:
        if u.client_level in level_counts_now:
            level_counts_now[u.client_level] += 1
    for u in users_prev:
        if u.client_level in level_counts_prev:
            level_counts_prev[u.client_level] += 1

    total_now = len(users_now)
    total_prev = len(users_prev)

    staked_now = level_counts_now[1]
    staked_prev = level_counts_prev[1]

    conversion_page_bot_now = (total_now / analytics_now * 100) if analytics_now > 0 else 0.0
    conversion_page_bot_prev = (total_prev / analytics_prev * 100) if analytics_prev > 0 else 0.0

    conversion_bot_staked_now = (total_now / staked_now * 100) if staked_now > 0 else 0.0
    conversion_bot_staked_prev = (total_prev / staked_prev * 100) if staked_prev > 0 else 0.0

    return [
        Statistic(title="Návštěvníci webu", value=analytics_now, change=calc_change(analytics_now, analytics_prev)),
        Statistic(title="Nezastakováno", value=level_counts_now[0], change=calc_change(level_counts_now[0], level_counts_prev[0])),
        Statistic(title="Zastakováno", value=level_counts_now[1], change=calc_change(level_counts_now[1], level_counts_prev[1])),
        Statistic(title="Affiliate", value=level_counts_now[2], change=calc_change(level_counts_now[2], level_counts_prev[2])),
        Statistic(title="Celkem v Botovi", value=total_now, change=calc_change(total_now, total_prev)),
        Statistic(title="Konverzní poměr (Stránka/Bot)", value=conversion_page_bot_now, is_ratio=True, change=calc_change(conversion_page_bot_now, conversion_page_bot_prev)),
        Statistic(title="Konverzní poměr (Bot/Staked)", value=conversion_bot_staked_now, is_ratio=True, change=calc_change(conversion_bot_staked_now, conversion_bot_staked_prev)),
    ]
