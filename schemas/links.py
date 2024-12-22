# schemas/links.py

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

class BaseLink(BaseModel):
    id: UUID
    bot_id: UUID
    is_faq: bool
    position: int
    parent: str
    child: str
        
    class Config:
        form_attributes = True

class CreateLink(BaseModel):
    bot_id: UUID
    is_faq: Optional[bool] = False
    position: int
    parent: str
    child: str
        
    class Config:
        form_attributes = True

class UpdateLink(BaseModel):
    position: Optional[int] = None
    parent: Optional[str] = None
    child: Optional[str] = None
        
    class Config:
        form_attributes = True

class ReadLink(BaseModel):
    id: UUID
    bot_id: UUID
    position: int
    parent: str
    child: str
        
    class Config:
        form_attributes = True