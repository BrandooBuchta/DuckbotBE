# schemas/user.py

from pydantic import BaseModel
from typing import Optional, List
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
    reference: Optional[str]
    rating: int
    academy_link: Optional[str]
    name: str
    username: Optional[str]
    created_at: datetime

class DeleteUsersRequest(BaseModel):
    user_ids: List[UUID]

class TargetCreate(BaseModel):
    user_id: UUID
    initial_investment: Optional[int] = 0
    monthly_addition: Optional[int] = 0
    duration: Optional[int] = 0
    currency: str
    is_dynamic: Optional[bool] = False
    quantity_affiliate_target: Optional[str] = None
    quality_affiliate_target: Optional[str] = None

class TargetUpdate(BaseModel):
    user_id: Optional[UUID] = None
    initial_investment: Optional[int] = None
    monthly_addition: Optional[int] = None
    duration: Optional[int] = None
    currency: Optional[str] = None
    is_dynamic: Optional[bool] = None
    quantity_affiliate_target: Optional[str] = None
    quality_affiliate_target: Optional[str] = None