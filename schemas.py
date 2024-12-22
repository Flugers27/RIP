from pydantic import BaseModel
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserCreate(BaseModel):
    email: str
    password: str

    def get_hashed_password(self):
        return pwd_context.hash(self.password)

class Token(BaseModel):
    access_token: str
    token_type: str
