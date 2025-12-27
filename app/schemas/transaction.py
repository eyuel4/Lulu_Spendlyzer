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
    card_id: int | None = None
    expense_category_id: int | None = None

class TransactionResponse(TransactionBase):
    id: int
    user_id: int
    card_id: int
    currency: str = "USD"
    created_at: datetime
    
    # Relationship fields (optional, populated when relationships are loaded)
    bank_name: str | None = None
    card_name: str | None = None
    expense_category_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_orm_with_relationships(cls, transaction):
        """Create response with relationship data"""
        data = {
            "id": transaction.id,
            "user_id": transaction.user_id,
            "card_id": transaction.card_id,
            "name": transaction.name,
            "merchant_name": transaction.merchant_name,
            "date": transaction.date,
            "amount": transaction.amount,
            "plaid_category": transaction.plaid_category,
            "custom_category": transaction.custom_category,
            "budget_type": transaction.budget_type,
            "month_id": transaction.month_id,
            "plaid_transaction_id": transaction.plaid_transaction_id or "",
            "currency": transaction.currency or "USD",
            "created_at": transaction.created_at,
            "bank_name": transaction.card.bank_name if transaction.card else None,
            "card_name": transaction.card.card_name if transaction.card else None,
            "expense_category_name": transaction.expense_category.name if transaction.expense_category else None
        }
        return cls(**data)

class TransactionRead(BaseModel):
    # ... fields ...
    model_config = ConfigDict(from_attributes=True) 