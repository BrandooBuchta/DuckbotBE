from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from schemas.user import UserCreate
from crud.user import create_or_update_user, get_all_users, get_user_by_id, update_user_name
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(".env")

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
        text = message.get("text", "").strip()

        user = get_user_by_id(db, user_id)

        if text == "/start":
            # Ulož/aktualizuj uživatele bez jména
            create_or_update_user(db, UserCreate(id=user_id, chat_id=chat_id))
            
            # Pošli Welcome Message
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": "Ahoj!"})

            # Pošli dotaz na jméno
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": "Jak ti mám říkat?"})

        else:
            # Pokud uživatel nemá jméno, aktuální text bereme jako jméno
            if user and user.name is None:
                # Uložíme jméno uživatele
                update_user_name(db, user_id, text)
                requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": f"Tvoje jméno je nyní uloženo jako {text}!"})
            else:
                # Pokud už jméno má, můžeme zde řešit další příkazy či logiku
                pass

    return {"ok": True}

@app.post("/send-message")
async def send_message_to_all_users(payload: BroadcastMessage, db: Session = Depends(get_db)):
    users = get_all_users(db)
    for user in users:
        # Pokud zpráva obsahuje {name}, nahradíme ji skutečným jménem (pokud má)
        text = payload.text
        if "{name}" in text:
            user_name = user.name if user.name else "kamaráde"
            text = text.replace("{name}", user_name)
        
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": user.chat_id, "text": text})

    return {"status": "Message sent to all users"}

@app.get("/")
async def root():
    return {"message": "Telegram Bot is running!"}
