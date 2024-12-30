from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, get_db
from schemas.user import UserCreate
from crud.user import create_or_update_user, get_all_users, get_user_by_id, update_user_name
from models.bot import Sequence
import os
import requests
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, PlainTextResponse
from routers.bot import router as bot_router
from routers.links import router as links_router
from routers.faq import router as faq_router
from routers.sequence import router as sequence_router

load_dotenv()

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

scheduler = BackgroundScheduler()

class BroadcastMessage(BaseModel):
    text: str

def send_message_to_user(bot_token: str, chat_id: str, message: str):
    telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    response = requests.post(
        telegram_api_url,
        json={"chat_id": chat_id, "text": message}
    )
    if response.status_code != 200:
        print(f"Failed to send message to {chat_id}: {response.text}")

def process_sequence(sequence: Sequence, db: Session):
    bot_token = BOT_TOKEN
    users_query = db.query(User).filter(User.bot_id == sequence.bot_id)

    if sequence.for_client:
        users_query = users_query.filter(User.is_in_betfin == True)
    elif sequence.for_new_client:
        users_query = users_query.filter(User.is_in_betfin == False)

    users = users_query.all()

    for user in users:
        send_message_to_user(bot_token, user.chat_id, sequence.message)

    if not sequence.repeat and not sequence.send_immediately:
        db.delete(sequence)
        db.commit()
        return

    if sequence.repeat:
        sequence.send_at = sequence.send_at + timedelta(days=sequence.interval)
        db.commit()

def schedule_sequences():
    db = next(get_db())
    sequences = db.query(Sequence).filter(Sequence.is_active == True).all()

    for sequence in sequences:
        initial_execution_time = sequence.starts_at or sequence.send_at
        if not initial_execution_time:
            continue

        scheduler.add_job(
            process_sequence,
            trigger=DateTrigger(run_date=initial_execution_time),
            args=[sequence, db],
            id=str(sequence.id),
        )

        if sequence.repeat:
            scheduler.add_job(
                process_sequence,
                trigger=IntervalTrigger(days=sequence.interval, start_date=initial_execution_time),
                args=[sequence, db],
                id=f"{sequence.id}_recurring",
            )

    scheduler.start()

@app.on_event("startup")
async def startup_event():
    schedule_sequences()
    print("Scheduler initialized and sequences are scheduled.")

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

@app.get("/")
async def root():
    return {"message": "Telegram Bot is running!"}

app.include_router(bot_router, prefix="/api/bot", tags=["Bots"])
app.include_router(links_router, prefix="/api/bot/academy-link", tags=["Academy Links"])
app.include_router(faq_router, prefix="/api/bot/faq", tags=["FAQ"])
app.include_router(sequence_router, prefix="/api/bot/sequence", tags=["Sequences"])
