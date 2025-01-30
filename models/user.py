# models/user.py

from sqlalchemy import Column, BigInteger, Boolean, String, Integer, DateTime
from database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.sql import func
from datetime import timedelta

class User(Base):
    __tablename__ = "telegram_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    is_client = Column(Boolean, default=False)
    academy_link = Column(String, nullable=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    