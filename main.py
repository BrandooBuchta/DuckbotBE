# main.py

from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from schemas.user import UserCreate
from crud.user import get_audience, update_user_name, get_current_user
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi.responses import PlainTextResponse
from datetime import datetime, timedelta
from routers.bot import router as bot_router
from routers.links import router as links_router
from routers.faq import router as faq_router
from routers.sequence import router as sequence_router
from apscheduler.schedulers.background import BackgroundScheduler
from crud.sequence import get_sequences, update_sequence, delete_sequence, get_sequence, update_send_at
from crud.vars import replace_variables
from crud.bot import get_bot
import logging
from pytz import timezone
from uuid import UUID
import uvicorn
from base64 import b64decode

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://don-simon-bot-manager-ui.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def format_events(events):
    lines = []
    for e in events:
        # Převod timestamp na čitelný formát (UTC)
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

@app.get("/")
async def root():
    return {"message": "Telegram Bot is running!"}

app.include_router(bot_router, prefix="/api/bot", tags=["Bots"])
app.include_router(links_router, prefix="/api/bot/academy-link", tags=["Academy Links"])
app.include_router(faq_router, prefix="/api/bot/faq", tags=["FAQ"])
app.include_router(sequence_router, prefix="/api/bot/sequence", tags=["Sequences"])

def processs_sequences(db: Session):
    logger.info("Starting to process sequences...")
    
    sequences, status = get_sequences(db)
    logger.info(f"Retrieved sequences: {sequences}, Status: {status}")

    if status != 200:
        logger.error(f"Failed to retrieve sequences from the database. {sequences}")
        return

    for sequence in sequences:
        logger.info(f"Processing sequence ID: {sequence.id}")
        
        users = get_audience(db, sequence.bot_id, sequence.for_client, sequence.for_new_client)
        logger.info(f"Found users: {users} for bot ID: {sequence.bot_id}")

        if not users:
            logger.warning(f"No users found for bot ID: {sequence.bot_id}")
            continue

        for user in users:
            logger.info(f"Sending message to user {user.chat_id}")
            send_message_to_user(db, sequence.bot_id, user.chat_id, sequence.message, sequence.check_status)

        if sequence.repeat:
            if sequence.interval:
                updated_date = sequence.send_at + timedelta(days=sequence.interval)
                update_sequence(db, sequence.id, {"send_at": updated_date, "starts_at": updated_date, "send_immediately": False})
                logger.info(f"Sequence {sequence.id} rescheduled to send_at: {updated_date}")
        else:
            update_sequence(db, sequence.id, {"send_at": None, "starts_at": None, "send_immediately": False, "is_active": True})

def send_message_to_user(db: Session, bot_id: UUID, chat_id: int, message: str, check_status: bool):
    bot, status = get_bot(db, bot_id)
    telegram_api_url = f"https://api.telegram.org/bot{b64decode(bot.token).decode()}"
    url = f"{telegram_api_url}/sendMessage"

    user = get_current_user(db, chat_id, bot_id)

    if not user:
        print("user not found ")
    
    data = {
        "chat_id": chat_id,
        "text": replace_variables(db, bot_id, chat_id, message),
        "parse_mode": "html"
    }
    
    if check_status:
        data["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "ANO", "callback_data": f"{user.id}|t"},
                {"text": "NE", "callback_data": f"{user.id}|f"},
            ]]
        }
    
    response = requests.post(url, json=data)
    response.raise_for_status()


# Scheduler function
def sequence_service():
    logger.info("Scheduler started scheduling...")
    db = next(get_db())
    processs_sequences(db)

# Initialize APScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    sequence_service,
    "interval",
    minutes=1,
    max_instances=10,  # Umožní až 10 instancí najednou
    misfire_grace_time=300  # Povolené zpoždění až 5 minut
)
scheduler.start()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down scheduler...")
    scheduler.shutdown()

if __name__ == "__main__":
    port = int(os.getenv("PORT"))
    uvicorn.run(app, host="0.0.0.0", port=port)
