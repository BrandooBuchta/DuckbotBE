# schemas/FAQs.py

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

class BaseFAQ(BaseModel):
    id: UUID
    bot_id: UUID
    is_faq: bool
    position: int
    parent: str
    child: str
        
    class Config:
        form_attributes = True

class CreateFAQ(BaseModel):
    bot_id: UUID
    is_faq: Optional[bool] = True
    position: int
    parent: str
    child: str
        
    class Config:
        form_attributes = True

class UpdateFAQ(BaseModel):
    position: Optional[int] = None
    parent: Optional[str] = None
    child: Optional[str] = None
        
    class Config:
        form_attributes = True

class ReadFAQ(BaseModel):
    id: UUID
    bot_id: UUID
    position: int
    parent: str
    child: str
        
    class Config:
        form_attributes = True