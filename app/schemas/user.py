from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    family_invitees: Optional[List[dict]] = None

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserRead(UserBase):
    id: int
    is_primary: bool
    family_group_id: Optional[int] = None
    created_at: Optional[datetime] = None
    auth_provider: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class UserResponse(UserBase):
    id: int
    is_primary: bool
    family_group_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class NotificationSettings(BaseModel):
    emailNotifications: bool = True
    pushNotifications: bool = True
    transactionAlerts: bool = True
    budgetAlerts: bool = True
    familyUpdates: bool = True
    marketingEmails: bool = False

class NotificationSettingsCreate(BaseModel):
    emailNotifications: bool = True
    pushNotifications: bool = True
    transactionAlerts: bool = True
    budgetAlerts: bool = True
    familyUpdates: bool = True
    marketingEmails: bool = False

class NotificationSettingsUpdate(BaseModel):
    emailNotifications: Optional[bool] = None
    pushNotifications: Optional[bool] = None
    transactionAlerts: Optional[bool] = None
    budgetAlerts: Optional[bool] = None
    familyUpdates: Optional[bool] = None
    marketingEmails: Optional[bool] = None

class PrivacySettings(BaseModel):
    profileVisibility: str = 'private'  # 'private' | 'family' | 'public'
    dataSharing: bool = False
    analyticsSharing: bool = True
    allowFamilyAccess: bool = True

class PrivacySettingsCreate(BaseModel):
    profileVisibility: str = 'private'  # 'private' | 'family' | 'public'
    dataSharing: bool = False
    analyticsSharing: bool = True
    allowFamilyAccess: bool = True

class PrivacySettingsUpdate(BaseModel):
    profileVisibility: Optional[str] = None  # 'private' | 'family' | 'public'
    dataSharing: Optional[bool] = None
    analyticsSharing: Optional[bool] = None
    allowFamilyAccess: Optional[bool] = None

class AccountType(BaseModel):
    type: str = 'personal'  # 'personal' | 'family'
    familyGroupId: Optional[int] = None

class UserAuth(BaseModel):
    login: str  # username or email
    password: str 