# routers/sequence.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas.bot import ReadSequence, UpdateSequence
from crud.sequence import create_sequence, get_sequence, get_all_sequences, update_sequence, delete_sequence
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
def post_sequence(bot_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not verify_token(db, bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    status = create_sequence(db, bot_id)
    if status != 200:
        raise HTTPException(status_code=400, detail="Stala se chyba při vytváření bota!")

    return {"detail": "Nový sequence byl úspěšně vytvořen!"}

@router.get("/{sequence_id}", response_model=ReadSequence)
def fetch_sequence(sequence_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    sequence, status = get_sequence(db, sequence_id)
    if status == 404:
        raise HTTPException(status_code=404, detail="Tento sequence nexistuje!")
        
    if not verify_token(db, sequence.bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return sequence

@router.get("/{bot_id}/all", response_model=List[ReadSequence])
def fetch_all_sequences(bot_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not verify_token(db, bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    sequences, status = get_all_sequences(db, bot_id)

    return sequences

@router.put("/{sequence_id}")
def put_sequence(sequence_id: UUID, update_sequence_body: UpdateSequence, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    sequence, status = get_sequence(db, sequence_id)

    if status == 404:
        raise HTTPException(status_code=404, detail="Tento sequence nexistuje!")

    if not verify_token(db, sequence.bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    update_sequence(db, sequence_id, update_sequence_body)

    return {"detail": "Úspěšně jsme upravili sequence!"}

@router.delete("/{sequence_id}")
def delete_sequence(sequence_id: UUID, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    sequence, status = get_sequence(db, sequence_id)

    if status == 404:
        raise HTTPException(status_code=404, detail="Tento sequence nexistuje!")

    if not verify_token(db, sequence.bot_id, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    delete_sequence(db, sequence_id)

    return {"detail": "Úspěšně jsme smazali sequence!"}