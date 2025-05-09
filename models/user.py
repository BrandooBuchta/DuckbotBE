# models/user.py

from sqlalchemy import Column, BigInteger, Boolean, String, Integer, DateTime
from database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.sql import func
from datetime import timedelta

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), nullable=False)
    from_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    client_level = Column(Integer, default=0)
    send_message_at = Column(DateTime(timezone=True), nullable=True)
    next_message_id = Column(Integer, default=0)
    reference = Column(String, nullable=True)
    rating = Column(Integer, default=0)
    academy_link = Column(String, nullable=True)
    name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
class Target(Base):
    __tablename__ = "target"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    bot_id = Column(UUID(as_uuid=True), nullable=False)
    initial_investment = Column(Integer, default=0)
    monthly_addition = Column(Integer, default=0)
    duration = Column(Integer, default=0)
    currency = Column(String, nullable=False)
    is_dynamic = Column(Boolean, default=False)
    quantity_affiliate_target = Column(String, nullable=True)
    quality_affiliate_target = Column(String, nullable=True)
    lang = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
