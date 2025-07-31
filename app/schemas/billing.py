from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class InvoiceSchema(BaseModel):
    id: int
    date: datetime
    amount: float
    status: str

    class Config:
        orm_mode = True

class SubscriptionSchema(BaseModel):
    id: int
    plan_name: str
    status: str
    renewal_date: Optional[datetime]
    payment_method: Optional[str]
    invoices: List[InvoiceSchema] = []

    class Config:
        orm_mode = True 