# routers/bot.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas.links import ReadLink, UpdateLink
from crud.links import create_link, get_link, get_all_links, update_link, delete_link
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
def create_academy_link(bot_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not verify_token(db, bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    status = create_link(db, bot_id)
    if status != 200:
        raise HTTPException(status_code=400, detail="Stala se chyba při vytváření bota!")

    return {"detail": "Nový link byl úspěšně vytvořen!"}

@router.get("/{link_id}", response_model=ReadLink)
def get_academy_link(link_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    link, status = get_link(db, link_id)
    if status == 404:
        raise HTTPException(status_code=404, detail="Tento link nexistuje!")
        
    if not verify_token(db, link.bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return link

@router.get("/{bot_id}/all", response_model=List[ReadLink])
def get_academy_links(bot_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not verify_token(db, bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    links, status = get_all_links(db, bot_id)

    return links

@router.put("/{link_id}")
def get_academy_link(link_id: UUID, update_link_body: UpdateLink, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    link, status = get_link(db, link_id)

    if status == 404:
        raise HTTPException(status_code=404, detail="Tento link nexistuje!")

    if not verify_token(db, link.bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    update_link(db, link_id, update_link_body)

    return {"detail": "Úspěšně jsme upravili link!"}

@router.delete("/{link_id}")
def delete_academy_link(link_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    link, status = get_link(db, link_id)

    if status == 404:
        raise HTTPException(status_code=404, detail="Tento link nexistuje!")

    if not verify_token(db, link.bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    delete_link(db, link_id)

    return {"detail": "Úspěšně jsme smazali link!"}