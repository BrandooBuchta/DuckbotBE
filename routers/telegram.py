from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.contacts import GetContactsRequest
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
        "session": session_string  # frontend si uloží
    }

@router.post("/broadcast")
async def broadcast_message(data: TelegramBroadcastSchema):
    try:
        session = data.session
        message = data.message

        async with TelegramClient(StringSession(session), API_ID, API_HASH) as client:
            # Načti seznam kontaktů
            result = await client(GetContactsRequest(hash=0))
            users = result.users
            sent = 0

            for user in users:
                if user.access_hash:
                    try:
                        peer = InputPeerUser(user.id, user.access_hash)
                        await client.send_message(peer, message)
                        sent += 1
                    except Exception as e:
                        print(f"⚠️ Nelze odeslat zprávu uživateli {user.id}: {e}")

            return {"success": True, "sent": sent}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při broadcastu: {e}")
