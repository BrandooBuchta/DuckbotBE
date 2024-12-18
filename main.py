from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from schemas.user import UserCreate
from crud.user import create_or_update_user, get_all_users, get_user_by_id, update_user_name
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOMAIN = os.getenv("VERCEL_URL")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

class BroadcastMessage(BaseModel):
    text: str

@app.on_event("startup")
async def set_webhook():
    callback_url = f"https://{DOMAIN}/webhook/"
    get_info_url = f"{TELEGRAM_API_URL}/getWebhookInfo"
    info_response = requests.get(get_info_url)
    if info_response.status_code == 200:
        info_data = info_response.json()
        if info_data.get("ok") and info_data["result"].get("url") == callback_url:
            print("Webhook is already set!")
            return

    webhook_url = f"{TELEGRAM_API_URL}/setWebhook"
    response = requests.post(webhook_url, data={"url": callback_url})
    if response.status_code == 200:
        data = response.json()
        if data.get("ok") and data.get("result") is True:
            print("Webhook successfully set!")
        else:
            print("Failed to set webhook:", data)
    else:
        print("Failed to set webhook:", response.text)

@app.post("/webhook/")
async def webhook(update: dict, db: Session = Depends(get_db)):
    if "message" in update:
        message = update["message"]
        user_id = message["from"]["id"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()

        user = get_user_by_id(db, user_id)

        if text == "/start":
            create_or_update_user(db, UserCreate(id=user_id, chat_id=chat_id))
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": "Ahoj!"})
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": "Jak ti mám říkat?"})
        else:
            if user and user.name is None:
                update_user_name(db, user_id, text)
                requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": f"Tvoje jméno je nyní uloženo jako {text}!"})
            else:
                # Další logika, pokud už jméno má
                pass

    return {"ok": True}

@app.post("/send-message")
async def send_message_to_all_users(payload: BroadcastMessage, db: Session = Depends(get_db)):
    users = get_all_users(db)
    for user in users:
        text = payload.text
        if "{name}" in text:
            user_name = user.name if user.name else "kamaráde"
            text = text.replace("{name}", user_name)
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": user.chat_id, "text": text})

    return {"status": "Message sent to all users"}

@app.get("/")
async def root():
    return {"message": "Telegram Bot is running!"}
