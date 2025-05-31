import os
import io
import subprocess
import tempfile

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.contacts import GetContactsRequest, AddContactRequest
from telethon.tl.types import InputPeerUser

from vokativ import sex, vokativ


def get_user_name(n):
    if sex(n) == "w":
        return vokativ(n, woman=True)
    return vokativ(n, woman=False) 

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
    phone_code_hash: str
    session: str

class TelegramBroadcastSchema(BaseModel):
    session: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    lang: str

@router.post("/start")
async def start_login(data: StartLoginRequest):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    try:
        sent = await client.send_code_request(data.phone)
        code_hash = sent.phone_code_hash
        session_string = client.session.save()
        await client.disconnect()
        return {
            "status": "code_sent",
            "session": session_string,
            "phone_code_hash": code_hash
        }
    except Exception as e:
        await client.disconnect()
        raise HTTPException(status_code=500, detail=f"Chyba při odesílání kódu: {e}")


@router.post("/confirm")
async def confirm_code(data: ConfirmCodeRequest):
    client = TelegramClient(StringSession(data.session), API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.sign_in(
                phone=data.phone,
                code=data.code,
                phone_code_hash=data.phone_code_hash
            )
        session_string = client.session.save()
    except SessionPasswordNeededError:
        raise HTTPException(status_code=403, detail="2FA is not supported yet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při přihlášení: {e}")
    finally:
        await client.disconnect()

    return {
        "status": "authenticated",
        "session": session_string
    }

@router.post("/broadcast")
async def broadcast_message(
    session: str = Form(...),
    message: str = Form(...),
    lang: str = Form(...),
    file: UploadFile = File(None)
):
    try:
        async with TelegramClient(StringSession(session), API_ID, API_HASH) as client:
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

            temp_video_path = None

            if file and file.content_type and file.content_type.startswith("video/"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_input:
                    temp_input.write(await file.read())
                    temp_input.flush()

                temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                temp_output_path = temp_output.name
                temp_output.close()

                subprocess.run([
                    "ffmpeg",
                    "-i", temp_input.name,
                    "-vf", "transpose=0",
                    "-metadata:s:v:0", "rotate=0",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-c:a", "copy",
                    temp_output_path
                ], check=True)

                temp_video_path = temp_output_path

            for user in contacts.users:
                if user.bot or not user.access_hash or user.id == me.id:
                    continue

                try:
                    name = get_user_name(user.first_name) if lang in ("cs", "sk") else user.first_name or "friend"
                    peer = InputPeerUser(user.id, user.access_hash)
                    caption = message.replace("{name}", name)

                    if file:
                        mime = file.content_type or ""

                        if mime.startswith("image/"):
                            file.file.seek(0)
                            await client.send_file(peer, file.file, caption=caption, supports_streaming=True)

                        elif mime.startswith("video/") and temp_video_path:
                            await client.send_file(peer, temp_video_path, caption=caption, supports_streaming=True)

                        else:
                            file.file.seek(0)
                            await client.send_file(peer, file.file, caption=caption, file_name=file.filename)
                    else:
                        await client.send_message(peer, caption, parse_mode="html")

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
