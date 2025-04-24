# schemas/links.py

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

class BaseLink(BaseModel):
    id: UUID
    bot_id: UUID
    position: int
    currently_assigned: int
    share: int
    parent: str
    child: str
        
    class Config:
        form_attributes = True

class CreateLink(BaseModel):
    bot_id: UUID
    currently_assigned: Optional[int] = 0
    share: Optional[int] = 0
    position: int
    parent: str
    child: str
        
    class Config:
        form_attributes = True

class UpdateLink(BaseModel):
    position: Optional[int] = None
    share: Optional[int] = None
    currently_assigned: Optional[int] = None
    parent: Optional[str] = None
    child: Optional[str] = None
        
    class Config:
        form_attributes = True

class ReadLink(BaseModel):
    id: UUID
    bot_id: UUID
    currently_assigned: int
    share: int
    position: int
    parent: str
    child: str
        
    class Config:
        form_attributes = True