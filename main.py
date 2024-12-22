from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, get_db
from schemas.user import UserCreate
from crud.user import create_or_update_user, get_all_users, get_user_by_id, update_user_name
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, PlainTextResponse
from datetime import datetime
from routers.bot import router as bot_router
from routers.links import router as links_router
from routers.faq import router as faq_router

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
DOMAIN = os.getenv("VERCEL_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

class BroadcastMessage(BaseModel):
    text: str

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

@app.on_event("startup")
async def set_webhook():
    if DOMAIN:
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
    else:
        print("No DOMAIN set, cannot set webhook.")

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

# @app.post("/webhook/")
# async def webhook(update: dict, db: Session = Depends(get_db)):
#     if "message" in update:
#         message = update["message"]
#         user_id = message["from"]["id"]
#         chat_id = message["chat"]["id"]
#         text = message.get("text", "").strip()

#         user = get_user_by_id(db, user_id)

#         if text == "/start":
#             create_or_update_user(db, UserCreate(id=user_id, chat_id=chat_id))
#             requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": "Ahoj!"})
#             requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": "Jak ti mám říkat?"})
#         elif text == "/events":
#             url = "https://lewolqdkbulwiicqkqnk.supabase.co/rest/v1/events?select=*&order=timestamp.asc"
#             headers = {
#                 "apikey": SUPABASE_ANON_KEY,
#                 "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
#             }

#             event_resp = requests.get(url, headers=headers)
#             if event_resp.status_code == 200:
#                 events_data = event_resp.json()
#                 formatted = format_events(events_data)
#                 requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": formatted})
#             else:
#                 requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": "Nepodařilo se načíst události."})
#         else:
#             if user and user.name is None:
#                 update_user_name(db, user_id, text)
#                 requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": f"Tvoje jméno je nyní uloženo jako {text}!"})
#             else:
#                 # Další logika, pokud už jméno má
#                 pass

#     return {"ok": True}

# @app.post("/send-message/{bot_id}")
# async def send_message_to_all_users(bot_id: UUID, payload: BroadcastMessage, db: Session = Depends(get_db)):
#     users = get_all_users(db)
#     for user in users:
#         text = payload.text
#         if "{name}" in text:
#             user_name = user.name if user.name else "kamaráde"
#             text = text.replace("{name}", user_name)
#         requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": user.chat_id, "text": text})

#     return {"status": "Message sent to all users"}

@app.get("/")
async def root():
    return {"message": "Telegram Bot is running!"}

app.include_router(bot_router, prefix="/api/bot", tags=["Bots"])
app.include_router(links_router, prefix="/api/bot/academy-link", tags=["Academy Links"])
app.include_router(faq_router, prefix="/api/bot/faq", tags=["FAQ"])