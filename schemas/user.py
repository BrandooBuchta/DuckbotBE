from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class UserBase(BaseModel):
    id: int
    bot_id: UUID
    chat_id: int
    is_in_betfin: bool = False
    name: Optional[str] = None

    class Config:
        form_attributes = True

class UserCreate(UserBase):
    bot_id: UUID
    chat_id: int
    is_in_betfin: bool = False
    name: Optional[str] = None
