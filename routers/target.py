from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas.user import TargetCreate, TargetUpdate
from crud.user import create_target, update_target, get_target
from uuid import UUID

router = APIRouter()

@router.post("/{user_id}")
def create_target_endpoint(user_id: UUID, data: TargetCreate, db: Session = Depends(get_db)):
    target, status = create_target(db, data)
    if status == 404:
        raise HTTPException(status_code=404, detail="User not found")
    return target

@router.put("/{user_id}")
def update_target_endpoint(user_id: UUID, data: TargetUpdate, db: Session = Depends(get_db)):
    target, status = update_target(db, user_id, data.dict(exclude_unset=True))
    if status == 404:
        raise HTTPException(status_code=404, detail="Target not found")
    return target

@router.get("/{user_id}")
def get_target_endpoint(user_id: UUID, db: Session = Depends(get_db)):
    target, status = get_target(db, user_id)
    if status == 404:
        raise HTTPException(status_code=404, detail="Target not found")
    return target
