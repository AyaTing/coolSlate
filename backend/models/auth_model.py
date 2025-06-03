from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"

class User(BaseModel):
    id: int
    email: EmailStr
    google_id: str 
    name: Optional[str] = None
    role: UserRole = UserRole.CUSTOMER
    created_at: datetime
    updated_at: datetime

    
class LoginResponse(BaseModel):
    user: User
    token: str


