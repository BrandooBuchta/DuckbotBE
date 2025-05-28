from fastapi import APIRouter, Form, Request, Response, Cookie, HTTPException
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from starlette.responses import JSONResponse
import os

router = APIRouter()

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
COOKIE_NAME = os.getenv("TG_SESSION_COOKIE", "tg_session")

clients = {}

@router.post("/start")
async def start_login(phone: str = Form(...)):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    await client.send_code_request(phone)
    clients[phone] = client
    return {"status": "code_sent"}

@router.post("/confirm")
async def confirm_code(
    response: Response,
    phone: str = Form(...),
    code: str = Form(...),
):
    client = clients.get(phone)
    if not client:
        raise HTTPException(status_code=400, detail="Session expired or not found")

    try:
        await client.sign_in(phone, code)
    except SessionPasswordNeededError:
        raise HTTPException(status_code=403, detail="2FA is not supported yet")

    session_string = client.session.save()
    await client.disconnect()
    clients.pop(phone, None)

    # Uloží session_string do HttpOnly cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_string,
        httponly=True,
        secure=False,  # true na HTTPS
        samesite="Lax",
        max_age=60 * 60 * 24 * 7,  # 7 dní
    )
    return {"status": "authenticated"}

@router.post("/broadcast")
async def broadcast_message(
    message: str = Form(...),
    session: str = Cookie(None),
):
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    client = TelegramClient(StringSession(session), API_ID, API_HASH)
    await client.start()
    success_count = 0

    async for user in client.iter_contacts():
        try:
            await client.send_message(user.id, message)
            success_count += 1
        except Exception:
            continue

    await client.disconnect()
    return {"status": "sent", "sent_to": success_count}
