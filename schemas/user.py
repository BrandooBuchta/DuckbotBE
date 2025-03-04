# schemas/user.py

from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class UserCreate(BaseModel):
    bot_id: UUID
    chat_id: int
    from_id: int
    name: Optional[str] = None

class UserBase(BaseModel):
    id: UUID
    bot_id: UUID
    from_id: int
    chat_id: int
    client_level: int = 0
    send_message_at: datetime
    next_message_id: int
    academy_link: str
    name: Optional[str] = None

    class Config:
        form_attributes = True
    
    