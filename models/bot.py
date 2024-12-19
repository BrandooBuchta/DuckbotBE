from sqlalchemy import Column, BigInteger, Boolean, String, Integer, ARRAY
from database import Base

class Bot(Base):
    __tablename__ = "bots"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=True)
    password = Column(String, nullable=True)
    token = Column(String, nullable=True)
    is_webhook_set = Column(Boolean, nullable=True)
    welcome_message = Column(String, nullable=True)
    follow_up_message = Column(String, nullable=True)
    follow_up_frequency = Column(Integer, nullable=True)
    start_message = Column(String, nullable=True)
    help_message = Column(String, nullable=True)
    contact_message = Column(String, nullable=True)
    welcome_message = Column(String, nullable=True)
    acadmey_links = Column(ARRAY(String), nullable=True)
    faq = Column(ARRAY(String), nullable=True) # TODO: Seperate table?
