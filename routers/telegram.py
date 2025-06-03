import os
import io
import subprocess
import tempfile
import cv2

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.contacts import GetContactsRequest, AddContactRequest
from telethon.tl.types import InputPeerUser, DocumentAttributeVideo

from vokativ import sex, vokativ


def get_user_name(n):
    if sex(n) == "w":
        return vokativ(n, woman=True)
    return vokativ(n, woman=False)

def get_video_metadata(path: str):
    try:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return None
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = int(frame_count / fps)
        cap.release()
        return width, height, duration
    except Exception:
        return None

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
            dialogs = await client.get_dialogs()

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
                import tempfile, shutil
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_input:
                    shutil.copyfileobj(file.file, temp_input)
                    temp_video_path = temp_input.name

            for user in contacts.users:
                if user.bot or not user.access_hash or user.id == me.id:
                    continue

                try:
                    name = get_user_name(user.first_name) if lang in ("cs", "sk") else user.first_name or "friend"
                    peer = InputPeerUser(user.id, user.access_hash)
                    personalized_msg = message.replace("{name}", name)

                    if file:
                        mime = file.content_type or ""

                        if mime.startswith("image/"):
                            file.file.seek(0)
                            await client.send_file(
                                peer,
                                file.file,
                                caption=None,
                                supports_streaming=True,
                                force_document=False
                            )
                            await client.send_message(peer, personalized_msg, parse_mode="html")

                        elif mime.startswith("video/") and temp_video_path:
                            metadata = get_video_metadata(temp_video_path)
                            if metadata:
                                w, h, duration = metadata
                            else:
                                w, h, duration = 720, 1280, 10  # fallback
                            
                            await client.send_file(
                                peer,
                                temp_video_path,
                                caption=None,
                                attributes=[
                                    DocumentAttributeVideo(duration=duration, w=w, h=h, supports_streaming=True)
                                ],
                                force_document=False
                            )
                            await client.send_message(peer, personalized_msg, parse_mode="html")

                        else:
                            file.file.seek(0)
                            await client.send_file(
                                peer,
                                file.file,
                                caption=None,
                                file_name=file.filename,
                                force_document=True
                            )
                            await client.send_message(peer, personalized_msg, parse_mode="html")
                    else:
                        await client.send_message(peer, personalized_msg, parse_mode="html")

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

@router.post("/broadcast-new")
async def broadcast_new_contacts(
    session: str = Form(...),
    message: str = Form(...),
    lang: str = Form(...),
    file: UploadFile = File(None)
):
    try:
        async with TelegramClient(StringSession(session), API_ID, API_HASH) as client:
            me = await client.get_me()

            # Kontakty před přidáním
            old_contacts = await client(GetContactsRequest(hash=0))
            old_ids = {user.id for user in old_contacts.users}

            # Přidání nových lidí z dialogu
            dialogs = await client.get_dialogs()
            for dialog in dialogs:
                if dialog.is_user and dialog.entity.id != me.id:
                    user = dialog.entity
                    if user.id not in old_ids:
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

            # Kontakty po přidání
            updated_contacts = await client(GetContactsRequest(hash=0))
            new_users = [
                u for u in updated_contacts.users
                if u.id not in old_ids and not u.bot and u.access_hash and u.id != me.id
            ]

            # Video příprava
            temp_video_path = None
            if file and file.content_type and file.content_type.startswith("video/"):
                import shutil
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_input:
                    shutil.copyfileobj(file.file, temp_input)
                    temp_video_path = temp_input.name

            sent = 0
            failed = []

            for user in new_users:
                try:
                    name = get_user_name(user.first_name) if lang in ("cs", "sk") else user.first_name or "friend"
                    peer = InputPeerUser(user.id, user.access_hash)
                    personalized_msg = message.replace("{name}", name)

                    if file:
                        mime = file.content_type or ""

                        if mime.startswith("video/") and temp_video_path:
                            metadata = get_video_metadata(temp_video_path)
                            if metadata:
                                w, h, duration = metadata
                            else:
                                w, h, duration = 720, 1280, 10
                            
                            await client.send_file(
                                peer,
                                temp_video_path,
                                caption=None,
                                attributes=[
                                    DocumentAttributeVideo(duration=duration, w=w, h=h, supports_streaming=True)
                                ],
                                force_document=False
                            )
                            await client.send_message(peer, personalized_msg, parse_mode="html")
                        else:
                            file.file.seek(0)
                            await client.send_file(
                                peer,
                                file.file,
                                caption=None,
                                file_name=file.filename,
                                force_document=True
                            )
                            await client.send_message(peer, personalized_msg, parse_mode="html")
                    else:
                        await client.send_message(peer, personalized_msg, parse_mode="html")

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
                "new_contacts": len(new_users),
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při broadcastu: {e}")
