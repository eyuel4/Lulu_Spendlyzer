from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FeatureRequestBase(BaseModel):
    description: str

class FeatureRequestCreate(FeatureRequestBase):
    pass

class FeatureRequestResponse(FeatureRequestBase):
    id: int
    user_id: Optional[int]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True 