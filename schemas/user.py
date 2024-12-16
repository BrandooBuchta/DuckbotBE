from pydantic import BaseModel

class UserBase(BaseModel):
    id: int
    chat_id: int
    is_in_betfin: bool = False
    name: Optional[str] = None

    class Config:
        form_attributes = True

class UserCreate(UserBase):
    pass
