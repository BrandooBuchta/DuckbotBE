from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from schemas.user import UserCreate
from crud.user import create_or_update_user, get_all_users, get_user_by_id, update_user_name
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi.responses import HTMLResponse

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOMAIN = os.getenv("VERCEL_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  # Váš Supabase anon key
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def format_events(events):
    lines = []
    for e in events:
        # Převod timestamp na čitelný formát (UTC)
        dt = datetime.utcfromtimestamp(e["timestamp"]).strftime("%Y-%m-%d %H:%M:%S UTC")
        # Vytvoření textu pro jeden event
        # (můžete použít například markdown, pokud je v botu povolen)
        line = (
            f"**{e['title']['cs']}**\n"
            f"- Jazyk: {e['language']}\n"
            f"- Čas: {dt}\n"
            f"- Min. stake: {e['minToStake']}\n"
            f"- URL: {e['url']}\n"
        )
        lines.append(line)
    return "\n".join(lines)


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

@app.get("/events")
async def events():
    # Zavoláme Supabase REST endpoint
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }

    url = "https://lewolqdkbulwiicqkqnk.supabase.co/rest/v1/events?select=*&order=timestamp.asc"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return format_events(resp.json())

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
        elif text == "/events":
            SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
            # Přímo voláme supabase endpoint
            url = "https://lewolqdkbulwiicqkqnk.supabase.co/rest/v1/events?select=*&order=timestamp.asc"
            headers = {
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
            }

            event_resp = requests.get(url, headers=headers)
            if event_resp.status_code == 200:
                events_data = event_resp.json()
                # Zformátujte data podle potřeby
                import json
                events_text = json.dumps(events_data, ensure_ascii=False, indent=2)
                # Odešleme text uživateli na Telegram
                requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": events_text})
            else:
                # Něco se nepovedlo, ohlásíme chybu nebo prázdný výsledek
                requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": "Nepodařilo se načíst události."})
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

@app.get("/ui", response_class=HTMLResponse)
async def ui():
    return """
    <html>
      <head><title>Send Message to All Users</title></head>
      <body>
        <h1>Odeslat zprávu všem uživatelům</h1>
        <form action="/send-message-form" method="post">
          <textarea name="text" rows="4" cols="50">Ahoj, {name}!</textarea><br/><br/>
          <input type="submit" value="Odeslat">
        </form>
      </body>
    </html>
    """

@app.post("/send-message-form", response_class=HTMLResponse)
async def send_message_form(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    text = form_data.get("text", "")
    users = get_all_users(db)

    for user in users:
        final_text = text
        if "{name}" in final_text:
            user_name = user.name if user.name else "kamaráde"
            final_text = final_text.replace("{name}", user_name)
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": user.chat_id, "text": final_text})

    return """
    <html>
      <body>
        <h2>Zpráva byla odeslána všem uživatelům!</h2>
        <a href="/ui">Zpět</a>
      </body>
    </html>
    """

@app.get("/")
async def root():
    return {"message": "Telegram Bot is running!"}
