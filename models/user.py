from sqlalchemy import Column, BigInteger, Boolean
from app.database import Base

class User(Base):
    __tablename__ = "telegram_users"
    id = Column(BigInteger, primary_key=True, index=True)
    chat_id = Column(BigInteger, nullable=False)
    is_in_betfin = Column(Boolean, default=False)
