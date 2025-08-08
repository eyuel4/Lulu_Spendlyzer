from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TwoFactorAuthBase(BaseModel):
    method: str = Field(..., description="2FA method: 'authenticator', 'sms', or 'email'")
    phone_number: Optional[str] = Field(None, description="Phone number for SMS 2FA")

class TwoFactorAuthCreate(TwoFactorAuthBase):
    pass

class TwoFactorAuthUpdate(BaseModel):
    method: Optional[str] = None
    phone_number: Optional[str] = None
    is_enabled: Optional[bool] = None

class TwoFactorAuthResponse(BaseModel):
    id: int
    user_id: int
    is_enabled: bool
    method: str
    phone_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TwoFactorAuthSettings(BaseModel):
    enabled: bool
    method: Optional[str] = None
    phone_number: Optional[str] = None
    backup_codes: Optional[List[str]] = None

class EnableTwoFactorRequest(BaseModel):
    method: str = Field(..., description="2FA method: 'authenticator', 'sms', or 'email'")
    phone_number: Optional[str] = Field(None, description="Phone number for SMS 2FA")
    verification_code: Optional[str] = Field(None, description="Verification code to confirm setup")

class TwoFactorSetupResponse(BaseModel):
    qr_code_url: Optional[str] = Field(None, description="QR code URL for authenticator apps")
    secret_key: Optional[str] = Field(None, description="Manual entry key for authenticator apps")
    backup_codes: List[str] = Field(..., description="Backup codes for account recovery")

class VerifyTwoFactorRequest(BaseModel):
    code: str = Field(..., description="2FA verification code")

class DisableTwoFactorRequest(BaseModel):
    password: Optional[str] = Field(None, description="Current password for verification")
    verification_code: Optional[str] = Field(None, description="2FA code for confirmation")