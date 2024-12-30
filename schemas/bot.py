# schemas/bot.py

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class BaseBot(BaseModel):
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None
    welcome_message: Optional[str] = None
    sequence_message_client: Optional[str] = None
    devs_currently_assigned: Optional[int] = 0
    share: Optional[int] = 5
    sequence_message_new_client: Optional[str] = None
    sequence_frequency: Optional[int] = None
    sequence_starts_at: Optional[datetime] = None
    start_message: Optional[str] = None
    help_message: Optional[str] = None
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
    welcome_message: Optional[str] = None
    sequence_message_client: Optional[str] = None
    devs_currently_assigned: Optional[int] = None
    devs_share: Optional[int] = None
    sequence_message_new_client: Optional[str] = None
    sequence_frequency: Optional[int] = None
    sequence_starts_at: Optional[datetime] = None
    start_message: Optional[str] = None
    help_message: Optional[str] = None
    support_contact: Optional[str] = None

    class Config:
        form_attributes = True

class SendMessage(BaseModel):
    message: str
    follow_up_message: Optional[str] = None
    send_after: Optional[float] = None
    for_new_client: bool
    for_client: bool

class UpdateSequence(BaseModel):
    name: Optional[str] = None
    message: Optional[str] = None
    send_at: Optional[datetime] = None
    starts_at: Optional[datetime] = None
    send_immediately: Optional[bool] = None
    interval: Optional[int] = None
    position: Optional[int] = None
    repeat: Optional[bool] = None
    for_client: Optional[bool] = None
    for_new_client: Optional[bool] = None
    is_active: Optional[bool] = None

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
    for_client: bool
    for_new_client: bool
    is_active: bool