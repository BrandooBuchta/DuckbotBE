from sqlalchemy.orm import Session
from models.bot import Bot, ScheduledMessage
from schemas.bot import SignUp, SignIn, SignInResponse, BaseBot, UpdateBot, CreateScheduledMessage
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


def get_bot(db: Session, bot_id: str):
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not db_bot:
        return None, 404
    return db_bot, 200


def sign_up(db: Session, bot: SignUp):
    decoded_password = _decode_base64_with_padding(bot.password)
    hashed_password = get_password_hash(decoded_password)

    db_bot = Bot(
        id=uuid.uuid4(),
        email=bot.email,
        password=hashed_password,
        welcome_message="*Vítej, {name}*",
        start_message="*Ahoj já jsem {botName} a jak mám říkat tobě?*",
        help_message="*Help message; {supportContact}*",

        token=b64encode(bot.token.encode()).decode(),
    )
    db.add(db_bot)
    db.commit()
    db.refresh(db_bot)
    return 200


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
        welcome_message=db_bot.welcome_message,
        sequence_message_client=db_bot.sequence_message_client,
        sequence_message_new_client=db_bot.sequence_message_new_client,
        sequence_frequency=db_bot.sequence_frequency,
        sequence_starts_at=db_bot.sequence_starts_at,
        start_message=db_bot.start_message,
        help_message=db_bot.help_message,
        support_contact=db_bot.support_contact,
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

def create_scheduled_message(db: Session, message: CreateScheduledMessage):
    db_message = ScheduledMessage(
        id=uuid.uuid4(),
        bot_id=message.bot_id,
        for_client=message.for_client,
        for_new_client=message.for_new_client,
        send_at=message.send_at,
        message=message.message,
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return 200