from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

class InvitationBase(BaseModel):
    family_group_id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    status: str = 'pending'

class InvitationCreate(InvitationBase):
    pass

class InvitationRead(InvitationBase):
    id: int
    token: str
    sent_at: datetime
    model_config = ConfigDict(from_attributes=True) 