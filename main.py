from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from schemas.user import UserCreate
from cruds.user import create_or_update_user
import os
import requests
from dotenv import load_dotenv

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

@app.post("/webhook/")
async def webhook(update: dict, db: Session = Depends(get_db)):
    if "message" in update:
        message = update["message"]
        user_id = message["from"]["id"]
        chat_id = message["chat"]["id"]

        user = UserCreate(id=user_id, chat_id=chat_id)
        create_or_update_user(db, user)

        text = f"Hello! Your chat ID is {chat_id}."
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

    return {"ok": True}

@app.get("/")
async def root():
    return {"message": "Telegram Bot is running!"}
