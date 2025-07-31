from sqlalchemy import String, Column, Integer, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class Transaction(BaseModel):
    __tablename__ = "transactions"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    plaid_transaction_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    merchant_name = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    plaid_category = Column(String, nullable=True)
    custom_category = Column(String, nullable=True)
    budget_type = Column(String, nullable=True)
    month_id = Column(String, nullable=False)

    user = relationship("User", back_populates="transactions")
    card = relationship("Card", back_populates="transactions") 