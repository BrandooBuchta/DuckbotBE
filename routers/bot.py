# routers/bot.py

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas.bot import SignIn, SignInResponse, SignUp, UpdateBot, SendMessage, PlainBot
from crud.bot import sign_in, sign_up, get_bot_by_email, get_bot, verify_token, update_bot, get_plain_bot
from crud.faq import get_all_formated_faqs
from crud.user import get_current_user, create_or_update_user, update_user_name, update_users_academy_link, get_user, set_is_client, create_user
from crud.vars import replace_variables
from crud.links import get_all_links, update_link
from schemas.user import UserCreate
from schemas.links import UpdateLink
from models.user import User
from models.bot import Sequence
from base64 import b64encode, b64decode
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Dict
import requests
from uuid import UUID
import random
import logging

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

DOMAIN = os.getenv("DOMAIN")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter()

def reset_all_links(db: Session, bot_id: UUID):
    links, status = get_all_links(db, bot_id)
    if status != 200 or not links:
        return

    for link_schema in links:
        update_link(db, link_schema.id, UpdateLink(currently_assigned=0))
        
def assing_academy_link(db: Session, bot_id: UUID, user_id: UUID):
    bot, status = get_bot(db, bot_id)
    links, status = get_all_links(db, bot_id)
    links_length = len(links)

    if all(link.currently_assigned == link.share for link in links) and bot.devs_currently_assigned == bot.devs_share:
        reset_all_links(db, bot_id)
        update_bot(db, bot_id, UpdateBot(devs_currently_assigned=0))

    random_number = random.randint(0, links_length)

    if random_number == links_length:
        if bot.devs_currently_assigned < bot.devs_share:
            update_users_academy_link(
                db,
                user_id,
                os.getenv(f"FOUNDERS_ACADEMY_LINK{'1' if bot.devs_currently_assigned % 2 == 0 else '2'}")
            )            
            update_bot(db, bot_id, UpdateBot(devs_currently_assigned=bot.devs_currently_assigned + 1))
            return
        else:
            assing_academy_link(db, bot_id, user_id)
            return

    link = links[random_number]
    if link.currently_assigned < link.share:
        update_users_academy_link(db, user_id, link.child)
        update_link(db, link.id, UpdateLink(currently_assigned=link.currently_assigned + 1))
    else:
        assing_academy_link(db, bot_id, user_id)

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

@router.put("/{bot_id}", response_model=UpdateBot)
def put_bot(bot_id: UUID, update_bot_body: UpdateBot, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    bot, status = get_bot(db, bot_id)

    if status == 404:
        raise HTTPException(status_code=404, detail="Tento bot neexistuje!")

    if not verify_token(db, bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    db_bot, status = update_bot(db, bot_id, update_bot_body)

    if status != 200:
        raise HTTPException(status_code=400, detail="Chyba při aktualizaci bota.")

    return UpdateBot(**db_bot.__dict__)

@router.get("/{bot_id}", response_model=PlainBot)
def fetch_bot(bot_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if status == 404:
        raise HTTPException(status_code=404, detail="Tento bot neexistuje!")

    if not verify_token(db, bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    db_bot, status = get_plain_bot(db, bot_id, update_bot_body)

    if status != 200:
        raise HTTPException(status_code=400, detail="Chyba při aktualizaci bota.")

    return db_bot

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

@router.post("/{bot_id}/webhook")
async def webhook(bot_id: UUID, update: dict, db: Session = Depends(get_db)):
    bot, status = get_bot(db, bot_id)
    telegram_api_url = f"https://api.telegram.org/bot{b64decode(bot.token).decode()}"

    if "callback_query" in update:
        callback_data = update['callback_query']['data']
        user_id_str, is_client = callback_data.split('|')
        user_id = UUID(user_id_str)

        set_is_client(db, user_id, is_client.lower() == "t")

        if (is_client == "t"):
            requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": update["callback_query"]["message"]["chat"]["id"], "text": f"<strong>Děkuju, nyní už vím že jsi součástí projektu a budu s tebou tak i nadále pracovat.</strong>", "parse_mode": "html"})
        else:
            requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": update["callback_query"]["message"]["chat"]["id"], "text": f"<strong>Děkuju, nyní už vím že ještě nejsi součástí projektu a budu s tebou tak i nadále pracovat ;)</strong>", "parse_mode": "html"})
        
    if "message" in update:
        message = update["message"]
        name = message["chat"]["first_name"]
        print("name: ", name)
        from_id = message["from"]["id"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip().lower()

        user = get_current_user(db, chat_id, bot_id)

        if text == "/start":
            if not user:
                user = create_user(db, UserCreate(from_id=from_id, chat_id=chat_id, bot_id=bot_id, name=name))
                assing_academy_link(db, bot_id, user.id)
            response = requests.post(f"{telegram_api_url}/sendMessage", json={
                "chat_id": chat_id,
                "text": replace_variables(db, bot_id, chat_id, bot.start_message),
                "parse_mode": "html"
            })

        # if text == "/start":
        #     if not user:
        #         user = create_or_update_user(db, UserCreate(from_id=from_id, chat_id=chat_id, bot_id=bot_id))
        #         assing_academy_link(db, bot_id, user.id)
        #         print("creating new user and assigning link")
        #         response = requests.post(f"{telegram_api_url}/sendMessage", json={
        #             "chat_id": chat_id,
        #             "text": replace_variables(db, bot_id, chat_id, bot.start_message),
        #             "parse_mode": "html"
        #         })

        #         if response.status_code != 200:
        #             print(f"Failed to send message: {response.text}")
        #         print("bot.start_message: ", bot.start_message)
        #         print("chat_id: ", chat_id)
        #     else:
        #         personalized_message = replace_variables(db, bot_id, chat_id, bot.welcome_message)
        #         response = requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": replace_variables(db, bot_id, chat_id, personalized_message), "parse_mode": "html"})

        #         if response.status_code != 200:
        #             print(f"Failed to send message: {response.text}")
        #         print("bot.start_message: ", bot.start_message)
        #         print("chat_id: ", chat_id)

        elif user and user.name is None:
            user_name = " ".join(word.capitalize() for word in text.split())
            update_user_name(db, user.id, user_name)
            personalized_message = bot.welcome_message.replace("{name}", user_name)
            requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": replace_variables(db, bot_id, chat_id, personalized_message), "parse_mode": "html"})

        else:
            if text == "/help":
                print(f"chat_id of {bot_id}: ", chat_id)
                requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": replace_variables(db, bot_id, chat_id, bot.help_message), "parse_mode": "html"})
            elif text == "/faq":
                faqs, status = get_all_formated_faqs(db, bot_id)
                requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": replace_variables(db, bot_id, chat_id, faqs), "parse_mode": "html"})
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
                    requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": formatted, "parse_mode": "html"})
                else:
                    requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": "Nepodařilo se načíst události.", "parse_mode": "html"})
            else:
                requests.post(f"{telegram_api_url}/sendMessage", json={"chat_id": chat_id, "text": "Neznámý příkaz. Použijte /help pro nápovědu.", "parse_mode": "html"})

    return {"ok": True}

@router.post("/callback")
async def handle_callback(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    logger.info(f"Raw callback data received: {data}")

    if "callback_query" not in data or "data" not in data["callback_query"]:
        logger.error("Invalid callback request received")
        raise HTTPException(status_code=400, detail="Invalid callback request")

    callback_query = data["callback_query"]
    callback_data = callback_query["data"]

    try:
        user_id_str, is_client = callback_data.split("|")
        user_id = UUID(user_id_str)
    except ValueError:
        logger.error(f"Invalid callback data format: {callback_data}")
        raise HTTPException(status_code=400, detail="Invalid callback data format")

    user = get_user(db, user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")

    bot, status = get_bot(db, user.bot_id)
    if status != 200:
        logger.error(f"Bot {user.bot_id} not found")
        raise HTTPException(status_code=404, detail="Bot not found")

    chat_id = callback_query["message"]["chat"]["id"]

    # Aktualizace uživatelských dat
    set_is_client(db, user_id, is_client.lower() == "t")

    # Odpověď na callback query
    telegram_api_url = f"https://api.telegram.org/bot{b64decode(bot.token).decode()}/answerCallbackQuery"
    requests.post(telegram_api_url, json={"callback_query_id": callback_query["id"], "text": "Odpověď uložena!"})

    # Poslání zprávy uživateli
    send_message_url = f"https://api.telegram.org/bot{b64decode(bot.token).decode()}/sendMessage"
    response = requests.post(send_message_url, json={
        "chat_id": chat_id,
        "text": "Děkujeme za odpověď! Vaše volba byla zaznamenána.",
        "parse_mode": "html"
    })

    if response.status_code != 200:
        logger.error(f"Failed to send message: {response.text}")

    return {"ok": True}
