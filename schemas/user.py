# schemas/user.py

from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class UserCreate(UserBase):
    bot_id: UUID
    chat_id: int
    from_id: int
    is_client: bool = False
    name: Optional[str] = None

class UserBase(BaseModel):
    id: UUID
    bot_id: UUID
    from_id: int
    chat_id: int
    is_client: bool = False
    name: Optional[str] = None

    class Config:
        form_attributes = True