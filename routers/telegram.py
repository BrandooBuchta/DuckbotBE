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
BASE_URL = "https://bot-configurator-api.onrender.com"

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

@router.get("/download/uploaded")
async def download_uploaded_video():
    file_path = "uploaded_test_video.mp4"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Soubor nenalezen")
    return FileResponse(file_path, media_type="video/mp4", filename="uploaded_test_video.mp4")

@router.get("/download/prepared")
async def download_prepared_video():
    file_path = "prepared_video.mp4"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Soubor nenalezen")
    return FileResponse(file_path, media_type="video/mp4", filename="prepared_video.mp4")

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
                    try:
                        await client(AddContactRequest(
                            id=dialog.entity.id,
                            first_name=dialog.entity.first_name or "NoName",
                            last_name=dialog.entity.last_name or "",
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
                with open("uploaded_test_video.mp4", "wb") as f:
                    shutil.copyfileobj(file.file, f)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_input:
                    with open("uploaded_test_video.mp4", "rb") as in_f:
                        shutil.copyfileobj(in_f, temp_input)
                    temp_video_path = temp_input.name

                shutil.copyfile(temp_video_path, "prepared_video.mp4")

                print(f"🟢 FE upload video:     {BASE_URL}/download/uploaded")
                print(f"🟢 Prepared video:      {BASE_URL}/download/prepared")

            for user in contacts.users:
                if user.bot or not user.access_hash or user.id == me.id:
                    continue

                try:
                    name = user.first_name or "friend"
                    caption = message.replace("{name}", name)
                    peer = InputPeerUser(user.id, user.access_hash)

                    if file:
                        if file.content_type.startswith("video/") and temp_video_path:
                            await client.send_file(
                                peer,
                                temp_video_path,
                                caption=caption,
                                supports_streaming=True,
                                force_document=False
                            )
                        else:
                            await client.send_file(
                                peer,
                                "uploaded_test_video.mp4",
                                caption=caption,
                                force_document=True
                            )
                    else:
                        await client.send_message(peer, caption)

                    sent += 1
                except Exception as e:
                    failed.append({"id": user.id, "error": str(e)})

            return {
                "success": True,
                "sent": sent,
                "failed": failed,
                "total": len(contacts.users),
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při broadcastu: {e}")