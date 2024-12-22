# schemas/bot.py

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class BaseBot(BaseModel):
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None
    is_webhook_set: Optional[bool] = None
    welcome_message: Optional[str] = None
    sequence_message_client: Optional[str] = None
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
    email: Optional[str] = None
    is_webhook_set: Optional[bool] = None
    welcome_message: Optional[str] = None
    sequence_message_client: Optional[str] = None
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

class CreateScheduledMessage(BaseModel):
    message: str
    send_at: datetime
    bot_id: UUID
    for_client: bool
    for_new_client: bool