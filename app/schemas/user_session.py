from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserSessionBase(BaseModel):
    device_info: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]

class UserSessionCreate(UserSessionBase):
    token_jti: str

class UserSessionResponse(UserSessionBase):
    id: int
    user_id: int
    token_jti: str
    is_current: bool
    created_at: datetime
    last_active_at: Optional[datetime]

    class Config:
        from_attributes = True 