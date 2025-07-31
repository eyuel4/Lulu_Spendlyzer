from pydantic import BaseModel, ConfigDict
from datetime import datetime

class CardBase(BaseModel):
    bank_name: str
    card_name: str
    last4: str

class CardCreate(CardBase):
    access_token: str
    user_id: int

class CardUpdate(BaseModel):
    bank_name: str | None = None
    card_name: str | None = None
    last4: str | None = None
    access_token: str | None = None

class CardResponse(CardBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CardRead(BaseModel):
    # ... fields ...
    model_config = ConfigDict(from_attributes=True) 