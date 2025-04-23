# models/bot.py

from sqlalchemy import Column, BigInteger, Boolean, String, Integer, ARRAY, Integer, DateTime, Float
from database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import timedelta
from sqlalchemy.sql import func

class Bot(Base):
    __tablename__ = "bots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=True)
    password = Column(String, nullable=True)
    token = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    bot_url = Column(String, nullable=True)
    support_contact = Column(String, nullable=True)
    is_event = Column(Boolean, nullable=True)
    event_capacity = Column(Integer, nullable=True)
    event_date = Column(DateTime(timezone=True), server_default=func.now())
    event_location = Column(String, nullable=True)
    event_name = Column(String, nullable=True)
    lang = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class BotList(Base):
    __tablename__ = "list"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), nullable=False)
    is_faq = Column(Boolean, nullable=False)
    position = Column(Integer, nullable=True)
    share = Column(Float, nullable=True)
    currently_assigned = Column(Integer, nullable=True)
    parent = Column(String, nullable=True)
    child = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Sequence(Base):
    __tablename__ = "sequence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    check_status = Column(Boolean, default=False)
    name = Column(String, nullable=True)
    bot_id = Column(UUID(as_uuid=True), nullable=False)
    message = Column(String, nullable=True)
    position = Column(Integer, nullable=True)
    levels = Column(ARRAY(Integer), default=[]) 
    repeat = Column(Boolean, nullable=True)
    is_active = Column(Boolean, nullable=True)
    send_at = Column(DateTime(timezone=True), nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=True)
    send_immediately = Column(Boolean, default=True)
    interval = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
