# schemas/bot.py

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class BaseBot(BaseModel):
    id: UUID
    name: Optional[str] = None
    video_url: Optional[str] = None
    bot_url: Optional[str] = None
    support_contact: Optional[str] = None
    instagram: Optional[str] = None
    is_event: Optional[bool] = False
    event_capacity: Optional[int] = 0
    event_date: Optional[datetime] = None
    event_location: Optional[str] = None
    event_name: Optional[str] = None
    lang: Optional[str] = None

    class Config:
        form_attributes = True

class PublicBot(BaseModel):
    id: UUID
    video_url: Optional[str] = None
    videos: Optional[List[str]] = []
    bot_url: Optional[str] = None
    is_event: Optional[bool] = False
    support_contact: Optional[str] = None
    instagram: Optional[str] = None
    event_capacity: Optional[int] = 0
    event_date: Optional[datetime] = None
    event_location: Optional[str] = None
    event_name: Optional[str] = None
    domain: Optional[str] = None
    videos: Optional[List[str]] = None
    lang: Optional[str] = None

    class Config:
        form_attributes = True


class SignUp(BaseModel):
    event_name: Optional[str] = None
    name: Optional[str] = None
    password: str
    token: str
    is_event: bool
    lang: Optional[str] = "cs"

    class Config:
        form_attributes = True

class SignIn(BaseModel):
    name: str
    password: str

    class Config:
        form_attributes = True

class SignInResponse(BaseModel):
    token: str
    bot: BaseBot

class UpdateBot(BaseModel):
    name: Optional[str] = None
    video_url: Optional[str] = None
    support_contact: Optional[str] = None
    instagram: Optional[str] = None
    is_event: Optional[bool] = False
    event_capacity: Optional[int] = 0
    event_date: Optional[datetime] = None
    event_location: Optional[str] = None
    event_name: Optional[str] = None
    domain: Optional[str] = None
    videos: Optional[List[str]] = None
    lang: Optional[str] = None

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

class Statistic(BaseModel):
    title: str
    value: float
    is_ratio: Optional[bool] = False
    change: Optional[float] = None
