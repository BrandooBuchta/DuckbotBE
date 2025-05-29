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
API_HASH = os.getenv(("TG_API_HASH"))

# Pydantic modely pro vstup
class StartLoginRequest(BaseModel):
    phone: str

class ConfirmCodeRequest(BaseModel):
    phone: str
    code: str

class TelegramBroadcastSchema(BaseModel):
    session: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    lang: str

@router.post("/start")
async def start_login(data: StartLoginRequest):
    async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        await client.connect()
        await client.send_code_request(data.phone)
    return {"status": "code_sent"}

@router.post("/confirm")
async def confirm_code(data: ConfirmCodeRequest):
    async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        await client.connect()
        try:
            await client.sign_in(data.phone, data.code)
        except SessionPasswordNeededError:
            raise HTTPException(status_code=403, detail="2FA is not supported yet")

        session_string = client.session.save()
    return {
        "status": "authenticated",
        "session": session_string
    }

def get_user_name(name: str | None) -> str:
    return name or "příteli"

@router.post("/broadcast")
async def broadcast_message(data: TelegramBroadcastSchema):
    try:
        async with TelegramClient(StringSession(data.session), API_ID, API_HASH) as client:
            me = await client.get_me()
            dialogs = await client.get_dialogs(limit=50)

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
                        pass

            contacts = await client(GetContactsRequest(hash=0))

            sent = 0
            failed = []

            for user in contacts.users:
                if user.bot or not user.access_hash or user.id == me.id:
                    continue

                try:
                    name = get_user_name(user.first_name) if data.lang in ("cs", "sk") else (user.first_name or "friend")
                    peer = InputPeerUser(user.id, user.access_hash)
                    await client.send_message(peer, data.message.replace("{name}", name), parse_mode="html")
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
