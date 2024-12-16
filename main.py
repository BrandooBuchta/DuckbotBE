from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from schemas.user import UserCreate
from cruds.user import create_or_update_user, get_all_users
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

# Initialize database
Base.metadata.create_all(bind=engine)

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

class BroadcastMessage(BaseModel):
    text: str

@app.post("/webhook/")
async def webhook(update: dict, db: Session = Depends(get_db)):
    if "message" in update:
        message = update["message"]
        user_id = message["from"]["id"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if text == "/start":
            # Ulož nebo aktualizuj uživatele
            user = UserCreate(id=user_id, chat_id=chat_id)
            create_or_update_user(db, user)

            # Odpověz "Welcome Message"
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": "Welcome Message"})

    return {"ok": True}

@app.post("/send-message")
async def send_message_to_all_users(payload: BroadcastMessage, db: Session = Depends(get_db)):
    users = get_all_users(db)

    for user in users:
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": user.chat_id, "text": payload.text})

    return {"status": "Message sent to all users"}

@app.get("/")
async def root():
    return {"message": "Telegram Bot is running!"}
