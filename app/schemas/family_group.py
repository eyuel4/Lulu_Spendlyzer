from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from pydantic import EmailStr

class FamilyGroupBase(BaseModel):
    owner_user_id: int
    family_name: str

class FamilyGroupCreate(FamilyGroupBase):
    pass

class FamilyGroupRead(FamilyGroupBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FamilyMemberInvite(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    role: str

class FamilyGroupSetupRequest(BaseModel):
    family_name: str
    invitees: List[FamilyMemberInvite] 