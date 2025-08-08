from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class TrustedDeviceBase(BaseModel):
    device_name: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    country_code: Optional[str] = None

class TrustedDeviceCreate(TrustedDeviceBase):
    remember_device: bool = True
    expiration_days: int = 7

class TrustedDeviceResponse(TrustedDeviceBase):
    id: int
    user_id: int
    device_name: str
    location: str
    country_code: str
    is_active: bool
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TrustedDeviceList(BaseModel):
    devices: List[TrustedDeviceResponse]
    total_count: int

class TrustedDeviceVerify(BaseModel):
    token: str
    device_hash: str

class TrustedDeviceRevoke(BaseModel):
    device_id: int

class TrustedDeviceAudit(BaseModel):
    device_id: int
    action: str  # 'create', 'use', 'revoke', 'expire'
    ip_address: str
    user_agent: str
    timestamp: datetime
    location: Optional[str] = None

    model_config = ConfigDict(from_attributes=True) 