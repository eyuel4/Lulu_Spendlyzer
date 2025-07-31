from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from typing import Union

class TransactionBase(BaseModel):
    name: str
    merchant_name: str | None = None
    date: date
    amount: float
    plaid_category: str | None = None
    custom_category: str | None = None
    budget_type: str | None = None
    month_id: str
    plaid_transaction_id: str

class TransactionCreate(TransactionBase):
    user_id: int
    card_id: int

class TransactionUpdate(BaseModel):
    name: str | None = None
    merchant_name: str | None = None
    date: Union[date, None] = None
    amount: float | None = None
    plaid_category: str | None = None
    custom_category: str | None = None
    budget_type: str | None = None
    month_id: str | None = None

class TransactionResponse(TransactionBase):
    id: int
    user_id: int
    card_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TransactionRead(BaseModel):
    # ... fields ...
    model_config = ConfigDict(from_attributes=True) 