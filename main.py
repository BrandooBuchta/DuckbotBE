from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from crud.sequence import get_sequences, update_sequence, delete_sequence
from crud.user import get_all_users
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import os
from dotenv import load_dotenv

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
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Scheduler Logic
def process_sequences(db: Session):
    sequences, _ = get_sequences(db)
    now = datetime.utcnow()

    for sequence in sequences:
        if not sequence.is_active:
            continue  # Skip inactive sequences

        # Set send_at to now if send_immediately is True
        if sequence.send_immediately:
            sequence.send_at = now
            update_sequence(db, sequence.id, {"send_at": sequence.send_at, "send_immediately": False})

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
    db = next(get_db())
    process_sequences(db)

# Initialize APScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(sequence_service, "interval", minutes=1)
scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Scheduler is running!"}
