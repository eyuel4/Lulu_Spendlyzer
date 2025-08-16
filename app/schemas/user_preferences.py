from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class UserPreferencesBase(BaseModel):
    default_transaction_method: Optional[str] = None
    theme: Optional[str] = 'light'
    notifications: Optional[Dict[str, bool]] = {
        'email': True,
        'push': True,
        'sms': False
    }
    date_format: Optional[str] = 'MM/DD/YYYY'
    currency: Optional[str] = 'USD'

class UserPreferencesCreate(UserPreferencesBase):
    user_id: int

class UserPreferencesUpdate(BaseModel):
    default_transaction_method: Optional[str] = None
    theme: Optional[str] = None
    notifications: Optional[Dict[str, bool]] = None
    date_format: Optional[str] = None
    currency: Optional[str] = None

class UserPreferencesResponse(UserPreferencesBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
