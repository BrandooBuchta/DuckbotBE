# main.py

from fastapi import FastAPI, Depends, Request, BackgroundTasks, Request
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from schemas.user import UserCreate, UserBase
from crud.user import get_audience, update_user_name, get_current_user, get_users_in_queue, send_message_to_user, get_user
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi.responses import PlainTextResponse, JSONResponse
from datetime import datetime, timedelta, timezone as dt_timezone
from routers.bot import router as bot_router
from routers.links import router as links_router
from routers.sequence import router as sequence_router
from routers.target import router as target_router
from crud.sequence import get_sequences, update_sequence, get_all_sequences
from crud.vars import replace_variables
from crud.bot import get_bot
from models.bot import Bot, Sequence
from uuid import UUID
import logging
from base64 import b64decode
from contextlib import contextmanager
from utils.messages import get_messages
import uvicorn
import uuid
from pytz import timezone as pytz_timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import or_
import re
from starlette import status
import json

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI()

YES_NO_LOCALIZED = {
    "cs": ("ANO", "NE"),
    "sk": ("ÁNO", "NIE"),
    "en": ("YES", "NO"),
    "esp": ("SÍ", "NO"),
}

with open("data/origins.json", "r", encoding="utf-8") as file:
    data = json.load(file)

app.add_middleware(
    CORSMiddleware,
    allow_origins=data.get("origins", []),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def format_events(events):
    lines = []
    for e in events:
        dt = datetime.utcfromtimestamp(e["timestamp"]).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = (
            f"{e['title']['cs']}\n"
            f"- Jazyk: {e['language']}\n"
            f"- Čas: {dt}\n"
            f"- Min. stake: {e['minToStake']}\n"
            f"- URL: {e['url']}\n"
        )
        lines.append(line.strip())
    return "\n\n".join(lines)

@app.get("/events")
async def events():
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }

    url = "https://lewolqdkbulwiicqkqnk.supabase.co/rest/v1/events?select=*&order=timestamp.asc"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    events_data = resp.json()
    formatted_text = format_events(events_data)
    return PlainTextResponse(content=formatted_text)

def send_sequence_to_user(db: Session, bot_id: UUID, chat_id: int, message: str, check_status: bool):
    bot, status = get_bot(db, bot_id)
    telegram_api_url = f"https://api.telegram.org/bot{b64decode(bot.token).decode()}"
    url = f"{telegram_api_url}/sendMessage"

    user = get_current_user(db, chat_id, bot_id)
    if not user:
        print("user not found")

    data = {
        "chat_id": chat_id,
        "text": replace_variables(db, bot_id, chat_id, message),
        "parse_mode": "html"
    }

    if check_status:
        yes_text, no_text = YES_NO_LOCALIZED.get(bot.lang, ("YES", "NO"))
        data["reply_markup"] = {
            "inline_keyboard": [[
                {"text": yes_text, "callback_data": f"{user.id}|t"},
                {"text": no_text, "callback_data": f"{user.id}|f"},
            ]]
        }


    response = requests.post(url, json=data)
    response.raise_for_status()

async def process_customers_trace():
    logger.info("✅ Spouštím úlohu process_customers_trace")
    db = SessionLocal()
    try:
        users = get_users_in_queue(db)
        logger.info(f"🔍 Nalezeno {len(users)} uživatelů ke zpracování.")
        for user in users:
            send_message_to_user(db, user)
    except Exception as e:
        logger.error(f"❌ Chyba při zpracování uživatelů: {str(e)}")
    finally:
        db.close()

@app.post("/run-customers-trace")
async def run_customers_trace(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_customers_trace)
    return {"status": "ok", "message": "Zpracování spuštěno"}

async def process_sequences():
    db = SessionLocal()
    logger.info("✅ Spouštím úlohu process_sequences")

    try:
        sequences, status = get_sequences(db)
        if status != 200:
            logger.info(f"❌ Nepodařilo se načíst sekvence: {sequences}")
            return

        for sequence in sequences:
            users = get_audience(db, sequence.bot_id, sequence.levels)
            if not users:
                logger.warning(f"⚠️ Žádní uživatelé pro sekvenci {sequence.id}")
                continue

            for user in users:
                send_sequence_to_user(db, sequence.bot_id, user.chat_id, sequence.message, sequence.check_status)

            if sequence.repeat and sequence.interval:
                updated_date = sequence.send_at + timedelta(days=sequence.interval)
                update_sequence(db, sequence.id, {"send_at": updated_date, "starts_at": updated_date, "send_immediately": False})
            else:
                update_sequence(db, sequence.id, {"send_at": None, "starts_at": None, "send_immediately": False, "is_active": False})

    except Exception as e:
        logger.error(f"❌ Chyba při zpracování sekvencí: {e}")
    finally:
        db.close()

@app.post("/run-sequences")
async def run_sequences(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_sequences)
    return {"status": "ok", "message": "Zpracování spuštěno"}

@app.get("/")
async def root():
    return {"message": "Telegram Bot is running!"}

# 🔁 Funkce pro generování event sekvencí
def create_event_sequences():
    logger.info("📅 Spouštím plánovač pro sekvence eventů")
    db = SessionLocal()
    try:
        bots = db.query(Bot).filter(
            or_(
                Bot.lang == "cs",
                Bot.lang == "sk"
            )
        ).all()
    
        for bot in bots:
            generate_sequences_for_bot(db, bot)
    except Exception as e:
        logger.error(f"❌ Chyba při vytváření event sekvencí: {e}")
    finally:
        db.close()

def generate_sequences_for_bot(db: Session, bot: Bot):
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }

    SUPABASE_URL = "https://lewolqdkbulwiicqkqnk.supabase.co/rest/v1/events?select=*&order=timestamp.asc"
    resp = requests.get(SUPABASE_URL, headers=headers)
    events = resp.json()

    existing_sequences, _ = get_all_sequences(db, bot.id)
    for seq in existing_sequences:
        if "Event" in seq.name:
            db.delete(seq)
    db.commit()

    for index, event in enumerate(events):
        europe_prague = pytz_timezone("Europe/Prague")
        event_time = datetime.fromtimestamp(event["timestamp"], tz=europe_prague)

        if event_time < datetime.now(dt_timezone.utc):
            continue

        sequence_name = f"Event {event['id']}"
        messages = get_messages(1, bot.lang, bot.is_event, bot.id)
        matching_message = next(
            (msg for msg in messages if msg.get("event") == event["title"]["en"]),
            None
        )
        if not matching_message:
            continue

        message_text = matching_message["content"]
        message_text = message_text.replace("{url}", event["url"])
        message_text = message_text.replace("{time}", event_time.strftime("%d. %m. %Y - %H:%M"))

        send_time = datetime.fromtimestamp(event["timestamp"] - 3600, tz=dt_timezone.utc)

        sequence = Sequence(
            id=uuid.uuid4(),
            bot_id=bot.id,
            name=sequence_name,
            position=index + 1,
            message=f"{message_text}",
            levels=[1],
            repeat=False,
            send_at=send_time,
            send_immediately=False,
            starts_at=send_time,
            is_active=True,
            check_status=False
        )

        db.add(sequence)

    db.commit()
    logger.info(f"✅ Pro bota {bot.id} vytvořeny nové sekvence eventů.")

scheduler = BackgroundScheduler()
scheduler.add_job(create_event_sequences, CronTrigger(day_of_week="mon", hour=10, minute=0))

@app.on_event("startup")
def start_scheduler():
    scheduler.start()
    create_event_sequences()

app.include_router(bot_router, prefix="/api/bot", tags=["Bots"])
app.include_router(sequence_router, prefix="/api/bot/sequence", tags=["Sequences"])
app.include_router(links_router, prefix="/api/bot/academy-link", tags=["Academy Links"])
app.include_router(target_router, prefix="/api/bot/target", tags=["Target"])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
