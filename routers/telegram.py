from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.contacts import GetContactsRequest, AddContactRequest
from telethon.tl.types import InputPeerUser

import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")

clients = {}

# Pydantic modely pro vstup
class StartLoginRequest(BaseModel):
    phone: str

class ConfirmCodeRequest(BaseModel):
    phone: str
    code: str

class TelegramBroadcastSchema(BaseModel):
    session: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

@router.post("/start")
async def start_login(data: StartLoginRequest):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    await client.send_code_request(data.phone)
    clients[data.phone] = client
    return {"status": "code_sent"}

@router.post("/confirm")
async def confirm_code(data: ConfirmCodeRequest):
    client = clients.get(data.phone)
    if not client:
        raise HTTPException(status_code=400, detail="Session expired or not found")

    try:
        await client.sign_in(data.phone, data.code)
    except SessionPasswordNeededError:
        raise HTTPException(status_code=403, detail="2FA is not supported yet")

    session_string = client.session.save()
    await client.disconnect()
    clients.pop(data.phone, None)

    return {
        "status": "authenticated",
        "session": session_string
    }

@router.post("/broadcast")
async def broadcast_message(data: TelegramBroadcastSchema):
    try:
        async with TelegramClient(StringSession(data.session), API_ID, API_HASH) as client:
            me = await client.get_me()

            # KROK 1: Získání konverzací
            dialogs = await client.get_dialogs(limit=50)

            # KROK 2: Přidání do kontaktů
            for dialog in dialogs:
                if dialog.is_user and dialog.entity.id != me.id:
                    user = dialog.entity
                    try:
                        await client(AddContactRequest(
                            id=user.id,
                            first_name=user.first_name or "NoName",
                            last_name=user.last_name or "",
                            phone="",
                            add_phone_privacy_exception=False
                        ))
                    except Exception:
                        pass  # už pravděpodobně v kontaktech nebo jiný problém

            # KROK 3: Získání všech kontaktů
            contacts = await client(GetContactsRequest(hash=0))

            # KROK 4: Odeslání zprávy
            sent = 0
            failed = []

            for user in contacts.users:
                if user.bot or not user.access_hash or user.id == me.id:
                    continue

                try:
                    peer = InputPeerUser(user.id, user.access_hash)
                    await client.send_message(peer, data.message.replace("{name}", user.first_name))
                    sent += 1
                except Exception as e:
                    failed.append({
                        "id": user.id,
                        "username": user.username,
                        "error": str(e)
                    })

            return {
                "success": True,
                "sent": sent,
                "failed": failed,
                "total": len(contacts.users),
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při broadcastu: {e}")
