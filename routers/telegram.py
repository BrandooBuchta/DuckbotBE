from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.contacts import GetContactsRequest, AddContactRequest
from telethon.tl.types import InputPeerUser
import os
from dotenv import load_dotenv
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
            print(f"✅ Přihlášen jako {me.id} ({me.username})")

            dialogs = await client.get_dialogs(limit=50)
            print(f"🔍 Nalezeno {len(dialogs)} dialogů")

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
                        print(f"👤 Přidán kontakt {user.id} ({user.username})")
                    except Exception as e:
                        print(f"⚠️ Nepodařilo se přidat {user.id}: {e}")

            contacts = await client(GetContactsRequest(hash=0))
            print(f"📇 Získáno {len(contacts.users)} kontaktů")

            sent = 0
            failed = []

            for user in contacts.users:
                if user.bot or not user.access_hash or user.id == me.id:
                    continue

                try:
                    name = get_user_name(user.first_name) if lang in ("cs", "sk") else user.first_name or "friend"
                    peer = InputPeerUser(user.id, user.access_hash)
                    caption = message.replace("{name}", name)

                    print(f"📤 Odesílám zprávu {user.id} ({user.username})")

                    if file:
                        mime = file.content_type or ""
                        print(f"   ➤ Soubor: {file.filename} ({mime})")

                        if mime.startswith("image/"):
                            await client.send_file(peer, file.file, caption=caption, force_document=False)
                        elif mime.startswith("video/"):
                            await client.send_file(peer, file.file, caption=caption, force_document=False, video_note=False)
                        else:
                            await client.send_file(peer, file.file, caption=caption, file_name=file.filename)
                    else:
                        await client.send_message(peer, caption, parse_mode="html")

                    sent += 1
                    print(f"✅ Odesláno {user.username or user.id}")
                except Exception as e:
                    print(f"❌ Nezdařilo se u {user.username or user.id}: {e}")
                    failed.append({
                        "id": user.id,
                        "username": user.username,
                        "error": str(e)
                    })

            print(f"📊 Hotovo – Úspěšně: {sent}, Selhalo: {len(failed)}")

            return {
                "success": True,
                "sent": sent,
                "failed": failed,
                "total": len(contacts.users),
            }

    except Exception as e:
        print(f"🔥 Kritická chyba: {e}")
        raise HTTPException(status_code=500, detail=f"Chyba při broadcastu: {e}")
