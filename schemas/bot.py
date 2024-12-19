from pydantic import BaseModel
from typing import Optional, List

class SignUp(BaseModel):
    name: str
    password: str
    token: str

    class Config:
        form_attributes = True

class SignIn(BaseModel):
    name: str
    password: str

    class Config:
        form_attributes = True

class SignInResponse(BaseModel):
    token: str

class UpdateBot(BaseModel):
    name: Optional[str] = None
    is_webhook_set: Optional[bool] = None
    welcome_message: Optional[str] = None
    follow_up_message: Optional[str] = None
    follow_up_frequency: Optional[int] = None
    start_message: Optional[str] = None
    help_message: Optional[str] = None
    contact_message: Optional[str] = None
    welcome_message: Optional[str] = None
    acadmey_links: Optional[List[str]] = None
    faq: Optional[List[str]] = None # TODO

    class Config:
        form_attributes = True
