# models/user.py

from sqlalchemy import Column, BigInteger, Boolean, String, Integer, DateTime
from database import Base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import timedelta

class User(Base):
    __tablename__ = "telegram_users"

    id = Column(BigInteger, primary_key=True, index=True)
    bot_id = Column(UUID(as_uuid=True), nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    is_in_betfin = Column(Boolean, default=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    