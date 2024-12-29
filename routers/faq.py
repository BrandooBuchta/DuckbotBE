# routers/bot.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas.faq import ReadFAQ, UpdateFAQ
from crud.faq import create_faq, get_faq, get_all_faqs, update_faq, delete_faq
from crud.bot import verify_token
from datetime import datetime
from typing import List
import requests
from uuid import UUID

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/{bot_id}")
def post_faq(bot_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not verify_token(db, bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    status = create_faq(db, bot_id)
    if status != 200:
        raise HTTPException(status_code=400, detail="Stala se chyba při vytváření bota!")

    return {"detail": "Nový faq byl úspěšně vytvořen!"}

@router.get("/{faq_id}", response_model=ReadFAQ)
def fetch_faq(faq_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    faq, status = get_faq(db, faq_id)
    if status == 404:
        raise HTTPException(status_code=404, detail="Tento faq nexistuje!")
        
    if not verify_token(db, faq.bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return faq

@router.get("/{bot_id}/all", response_model=List[ReadFAQ])
def fetch_all_faqs(bot_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    print ("bot_id: ", bot_id, " token: ", token)
    if not verify_token(db, bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    faqs, status = get_all_faqs(db, bot_id)

    return faqs

@router.put("/{faq_id}")
def put_faq(faq_id: UUID, update_faq_body: UpdateFAQ, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    faq, status = get_faq(db, faq_id)

    if status == 404:
        raise HTTPException(status_code=404, detail="Tento faq nexistuje!")

    if not verify_token(db, faq.bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    update_faq(db, faq_id, update_faq_body)

    return {"detail": "Úspěšně jsme upravili faq!"}

@router.delete("/{faq_id}")
def delete_faq(faq_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    faq, status = get_faq(db, faq_id)

    if status == 404:
        raise HTTPException(status_code=404, detail="Tento faq nexistuje!")

    if not verify_token(db, faq.bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    delete_faq(db, faq_id)

    return {"detail": "Úspěšně jsme smazali faq!"}