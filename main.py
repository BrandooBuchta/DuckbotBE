from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from schemas.user import UserCreate
from crud.user import create_or_update_user, get_all_users, get_user_by_id, update_user_name
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, PlainTextResponse
from datetime import datetime, timedelta
from routers.bot import router as bot_router
from routers.links import router as links_router
from routers.faq import router as faq_router
from routers.sequence import router as sequence_router
from apscheduler.schedulers.background import BackgroundScheduler
from crud.sequence import get_sequences, update_sequence, delete_sequence
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://localhost:3000"
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
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

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

# Scheduler Logic
def process_sequences(db: Session):
    logger.info("Processing sequences...")
    sequences, _ = get_sequences(db)
    now = datetime.utcnow()

    for sequence in sequences:
        if not sequence.is_active:
            continue  # Skip inactive sequences

        # Set send_at based on conditions
        if sequence.send_immediately:
            sequence.send_at = now
            update_sequence(db, sequence.id, {"send_at": sequence.send_at, "send_immediately": False})
        elif sequence.starts_at:
            sequence.send_at = sequence.starts_at
            update_sequence(db, sequence.id, {"send_at": sequence.send_at})

        # If send_at is due
        if sequence.send_at and sequence.send_at <= now:
            # Filter users based on sequence conditions
            users = get_all_users(db, sequence.bot_id)
            if sequence.for_new_client:
                users = [user for user in users if not user.is_in_betfin]
            elif sequence.for_client:
                users = [user for user in users if user.is_in_betfin]

            # Send messages to users
            for user in users:
                send_message_to_user(sequence.message, user.chat_id)

            # Handle repeating or deletion of the sequence
            if sequence.repeat and sequence.interval:
                sequence.send_at = sequence.send_at + timedelta(days=sequence.interval)
                update_sequence(db, sequence.id, {"send_at": sequence.send_at})
            else:
                delete_sequence(db, sequence.id)

def send_message_to_user(message, chat_id):
    """Sends a message to a user using the Telegram API."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    response = requests.post(url, json=data)
    response.raise_for_status()

# Scheduler function
def sequence_service():
    logger.info("Scheduler started scheduling...")
    db = next(get_db())
    process_sequences(db)

# Initialize APScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(sequence_service, "interval", minutes=1)
scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down scheduler...")
    scheduler.shutdown()
