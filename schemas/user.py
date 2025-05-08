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
    username: Optional[str] = None

class UserBase(BaseModel):
    id: UUID
    bot_id: UUID
    from_id: int
    chat_id: int
    client_level: int = 0
    send_message_at: Optional[datetime] = None
    next_message_id: Optional[int] = 0
    academy_link: str
    name: Optional[str] = None

    class Config:
        form_attributes = True

class UsersReference(BaseModel):
    name: str
    content: str
    rating: int
    created_at: datetime
    
class PublicUser(BaseModel):
    id: UUID
    client_level: int
    reference: str
    rating: int
    academy_link: str
    name: str
    username: str
    created_at: datetime
