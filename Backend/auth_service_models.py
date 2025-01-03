from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date

class User(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    birth_date: Optional[date] = None
    username: str
    password: str

class UserInDB(User):
    id: int
