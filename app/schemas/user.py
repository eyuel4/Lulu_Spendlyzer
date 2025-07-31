from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    is_primary: bool = True
    family_group_id: Optional[int] = None
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    auth_provider: str = 'local'
    provider_id: Optional[str] = None

class UserCreate(UserBase):
    password: str
    family_invitees: Optional[List[dict]] = None

class UserRead(UserBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    password: str | None = None

class UserResponse(UserBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserAuth(BaseModel):
    login: str  # username or email
    password: str 