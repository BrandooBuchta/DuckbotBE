from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import os

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

class BroadcastRequest(BaseModel):
    session: str
    message: str

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
async def broadcast_message(data: BroadcastRequest):
    if not data.session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    client = TelegramClient(StringSession(data.session), API_ID, API_HASH)
    await client.start()
    success_count = 0

    async for user in client.iter_contacts():
        try:
            await client.send_message(user.id, data.message)
            success_count += 1
        except Exception:
            continue

    await client.disconnect()
    return {"status": "sent", "sent_to": success_count}
