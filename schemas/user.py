from pydantic import BaseModel

class UserBase(BaseModel):
    id: int
    chat_id: int
    is_in_betfin: bool = False

    class Config:
        orm_mode = True

class UserCreate(UserBase):
    pass
