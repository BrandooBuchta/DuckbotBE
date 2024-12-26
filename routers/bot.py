# routers/bot.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas.bot import SignIn, SignInResponse, SignUp, UpdateBot, SendMessage
from crud.bot import sign_in, sign_up, get_bot_by_email, get_bot, verify_token, update_bot
from crud.faq import get_all_formated_faqs
from crud.user import get_user_by_id, create_or_update_user, update_user_name
from schemas.user import UserCreate
from base64 import b64encode, b64decode
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import List
import requests
from uuid import UUID

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

DOMAIN = os.getenv("DOMAIN")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  

router = APIRouter()

def replace_variables(db: Session, bot_id: UUID, user_id: int, message: str):
    bot, status = get_bot(db, bot_id)
    user = get_user_by_id(db, user_id)

    def get_closest_event(event_type: str) -> str:
        url = "https://lewolqdkbulwiicqkqnk.supabase.co/rest/v1/events"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
        }
        params = {
            "select": "*",
            "order": "timestamp.asc",
            "event_type": f"eq.{event_type}"  # Filter by event_type
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            events = response.json()
            if events:
                # Return the URL of the closest event
                return events[0]["url"]
        return "Žádné události nenalezeny"

    variables = [
        {
            "key": "name",
            "value": user.name if user and user.name else "uživateli"
        },
        {
            "key": "bot_name",
            "value": bot.name if bot and bot.name else "tvůj bot"
        },
        {
            "key": "support_contact",
            "value": bot.support_contact if bot and bot.support_contact else "podpora"
        },
        {
            "key": "launch_for_begginers",
            "value": get_closest_event("launch_for_begginers")
        },
        {
            "key": "build_your_business",
            "value": get_closest_event("build_your_business")
        },
        {
            "key": "opportunity_call",
            "value": get_closest_event("opportunity_call")
        },
        {
            "key": "academy_link",
            "value": "https://academy.example.com"
        },
    ]

    for var in variables:
        message = message.replace(f"{{{var['key']}}}", var["value"] or "neznámá hodnota")

    return message

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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

@router.post("/sign-up")
def create_bot(sign_up_body: SignUp, db: Session = Depends(get_db)):
    bot, status = get_bot_by_email(db, sign_up_body.name)
    if status == 200:
        raise HTTPException(status_code=400, detail="Tento bot už existuje!")

    sign_up_status = sign_up(db, sign_up_body)
    if sign_up_status != 200:
        raise HTTPException(status_code=400, detail="Stala se chyba při vytváření bota.")
    return {"detail": "Nový bot byl úspěšně vytvořen!"}

@router.post("/sign-in", response_model=SignInResponse)
def login_bot(sign_in_body: SignIn, db: Session = Depends(get_db)):
    res, sign_in_status = sign_in(db, sign_in_body)

    if sign_in_status == 404:
        raise HTTPException(status_code=404, detail="Bot s tímto jménem neexistuje.")
    if sign_in_status == 400:
        raise HTTPException(status_code=400, detail="Zadané heslo nebylo správné.")
    return res

@router.post("/sign-in", response_model=SignInResponse)
def login_bot(sign_in_body: SignIn, db: Session = Depends(get_db)):
    res, sign_in_status = sign_in(db, sign_in_body)

    if sign_in_status == 404:
        raise HTTPException(status_code=404, detail="Bot s tímto jménem neexistuje.")
    if sign_in_status == 400:
        raise HTTPException(status_code=400, detail="Zadané heslo nebylo správné.")
    return res

@router.put("/{bot_id}", response_model=UpdateBot)
def update_academy_faq(bot_id: UUID, update_bot_body: UpdateBot, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    bot, status = get_bot(db, bot_id)

    if status == 404:
        raise HTTPException(status_code=404, detail="Tento bot neexistuje!")

    if not verify_token(db, bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    db_bot, status = update_bot(db, bot_id, update_bot_body)

    if status != 200:
        raise HTTPException(status_code=400, detail="Chyba při aktualizaci bota.")

    return UpdateBot(**db_bot.__dict__)

@router.post("/{bot_id}/set-webhook")
async def set_webhook(bot_id: UUID, db: Session = Depends(get_db)):
    bot, status = get_bot(db, bot_id)
    telegram_api_url = f"https://api.telegram.org/bot{b64decode(bot.token).decode()}"

    if DOMAIN:
        callback_url = f"{DOMAIN}/bot/{bot_id}/webhook"
        get_info_url = f"{telegram_api_url}/getWebhookInfo"
        info_response = requests.get(get_info_url)
        if info_response.status_code == 200:
            info_data = info_response.json()
            if info_data.get("ok") and info_data["result"].get("url") == callback_url:
                print("Webhook is already set!")
                return callback_url

        webhook_url = f"{telegram_api_url}/setWebhook"
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

@router.delete("/{bot_id}/delete-webhook")
async def delete_webhook(bot_id: UUID, db: Session = Depends(get_db)):
    bot, status = get_bot(db, bot_id)
    if status != 200:
        raise HTTPException(status_code=404, detail="Bot not found.")

    telegram_api_url = f"https://api.telegram.org/bot{b64decode(bot.token).decode()}"

    if DOMAIN:
        webhook_url = f"{telegram_api_url}/deleteWebhook"
        response = requests.post(webhook_url)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return {"detail": "Webhook successfully deleted!"}
            else:
                raise HTTPException(status_code=400, detail=f"Failed to delete webhook: {data.get('description', 'Unknown error')}")
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to delete webhook: {response.text}")
    else:
        raise HTTPException(status_code=400, detail="No DOMAIN set, cannot delete webhook.")

@router.get("/{bot_id}/webhook-info")
async def get_webhook_info(bot_id: UUID, db: Session = Depends(get_db)) -> dict:
    bot, status = get_bot(db, bot_id)
    if status != 200:
        raise HTTPException(status_code=404, detail="Bot not found.")

    telegram_api_url = f"https://api.telegram.org/bot{b64decode(bot.token).decode()}"

    if DOMAIN:
        callback_url = f"{DOMAIN}/bot/{bot_id}/webhook"
        get_info_url = f"{telegram_api_url}/getWebhookInfo"
        info_response = requests.get(get_info_url)

        if info_response.status_code == 200:
            info_data = info_response.json()
            if info_data.get("ok"):
                webhook_url = info_data["result"].get("url")
                return { "webhook_info": webhook_url == callback_url }

    return { "webhook_info": False }

@router.post("/{bot_id}/send-message")
async def send_message(bot_id: UUID, body: SendMessage, db: Session = Depends(get_db)):
    bot, status = get_bot(db, bot_id)
    print(f"Message: {body.message}\nFollow-up Message: {body.follow_up_message}\nSend after: {body.send_after}\nFor Client: {body.for_client}\nFor New Client: {body.for_new_client}\n")


@router.post("/{bot_id}/webhook")
async def webhook(bot_id: UUID, update: dict, db: Session = Depends(get_db)):
    bot, status = get_bot(db, bot_id)
    telegram_api_url = f"https://api.telegram.org/bot{b64decode(bot.token).decode()}"

    if "message" in update:
        message = update["message"]
        user_id = message["from"]["id"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()

        user = get_user_by_id(db, user_id)

        if text == "/start":
            if not user or user.name is None:
                create_or_update_user(db, UserCreate(id=user_id, chat_id=chat_id, bot_id=bot_id))
                requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": bot.start_message})
            else:
                personalized_message = replace_variables(db, bot_id, user_id, bot.welcome_message)
                requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": personalized_message})
        elif not user or user.name is None:
            update_user_name(db, user_id, text)
            personalized_message = bot.welcome_message.replace("{name}", text)
            requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": personalized_message})
        else:
            if text == "/help":
                requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": bot.help_message})
            elif text == "/faq":
                faqs, status = get_all_formated_faqs(db, bot_id)
                requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": faqs})
            elif text == "/events":
                url = "https://lewolqdkbulwiicqkqnk.supabase.co/rest/v1/events?select=*&order=timestamp.asc"
                headers = {
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
                }

                event_resp = requests.get(url, headers=headers)
                if event_resp.status_code == 200:
                    events_data = event_resp.json()
                    formatted = format_events(events_data)
                    requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": formatted})
                else:
                    requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": "Nepodařilo se načíst události."})
            else:
                requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": "Neznámý příkaz. Použijte /help pro nápovědu."})

    return {"ok": True}
