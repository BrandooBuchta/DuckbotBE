# schemas/bot.py

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class BaseBot(BaseModel):
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None
    devs_currently_assigned: Optional[int] = 0
    ss_url: Optional[str] = None
    ss_landing_url: Optional[str] = None
    devs_share: Optional[int] = 10
    support_contact: Optional[str] = None

    class Config:
        form_attributes = True

class SignUp(BaseModel):
    name: str
    email: str
    password: str
    token: str

    class Config:
        form_attributes = True

class SignIn(BaseModel):
    email: str
    password: str

    class Config:
        form_attributes = True

class SignInResponse(BaseModel):
    token: str
    bot: BaseBot

class UpdateBot(BaseModel):
    name: Optional[str] = None
    devs_currently_assigned: Optional[int] = None
    devs_share: Optional[int] = None
    ss_url: Optional[str] = None
    ss_landing_url: Optional[str] = None
    support_contact: Optional[str] = None

    class Config:
        form_attributes = True

class PlainBot(BaseModel):
    name: str
    support_contact: str

    class Config:
        form_attributes = True

class UpdateSequence(BaseModel):
    name: Optional[str] = None
    message: Optional[str] = None
    send_at: Optional[datetime] = None
    starts_at: Optional[datetime] = None
    check_status: Optional[bool] = None
    send_immediately: Optional[bool] = None
    interval: Optional[int] = None
    position: Optional[int] = None
    repeat: Optional[bool] = None
    levels: List[int] = []
    is_active: Optional[bool] = None
    check_status: Optional[bool] = None

class ReadSequence(BaseModel):
    id: UUID
    bot_id: UUID
    name: str
    message: str
    position: int
    send_at: Optional[datetime]
    starts_at: Optional[datetime]
    send_immediately: bool
    interval: Optional[int]
    repeat: bool
    levels: List[int] = []
    is_active: bool
    check_status: bool