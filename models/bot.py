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
    email = Column(String, nullable=True)
    password = Column(String, nullable=True)
    token = Column(String, nullable=True)
    welcome_message = Column(String, nullable=True)
    sequence_frequency = Column(Integer, nullable=True)
    sequence_starts_at = Column(DateTime(timezone=True))
    sequence_message_client = Column(String, nullable=True)
    sequence_message_new_client = Column(String, nullable=True)
    devs_share = Column(Float, nullable=True)
    devs_currently_sent = Column(Integer, nullable=True)
    start_message = Column(String, nullable=True)
    help_message = Column(String, nullable=True)
    support_contact = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class BotList(Base):
    __tablename__ = "list"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), nullable=False)
    is_faq = Column(Boolean, nullable=False)
    position = Column(Integer, nullable=True)
    share = Column(Float, nullable=True)
    currently_sent = Column(Integer, nullable=True)
    parent = Column(String, nullable=True)
    child = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ScheduledMessage(Base):
    __tablename__ = "scheduled_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), nullable=False)
    send_at = Column(DateTime(timezone=True), server_default=func.now())
    message = Column(String, nullable=True)
    for_new_client = Column(Boolean, nullable=True)
    for_client = Column(Boolean, nullable=True)
