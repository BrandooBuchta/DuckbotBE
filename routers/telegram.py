from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
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
        client = TelegramClient(StringSession(data.session), API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            raise HTTPException(status_code=401, detail="Unauthorized Telegram session")

        async for user in client.iter_contacts():
            if user.bot or not user.access_hash:
                continue
            try:
                await client.send_message(user.id, data.message)
            except Exception as e:
                print(f"❌ Nepodařilo se odeslat zprávu uživateli {user.id}: {e}")

        await client.disconnect()
        return {"status": "ok"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při broadcastu: {str(e)}")
