"""
Transaction Type model for categorizing transactions
(Income, Expense, Transfer, Cash, Check Withdrawn, Wire)
"""
from sqlalchemy import String, Column, Integer, Text, Boolean
from .base import BaseModel


class TransactionType(BaseModel):
    """
    Represents different types of transactions in the system.
    System-wide metadata that applies to all users.
    """
    __tablename__ = "transaction_types"

    name = Column(String(50), unique=True, nullable=False, index=True)  # Income, Expense, Transfer, etc.
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)  # Icon name/SVG path for UI
    color = Column(String(20), nullable=True)  # Color code for UI (e.g., 'text-green-600')
    is_active = Column(Boolean, default=True, index=True)

    def __repr__(self):
        return f"<TransactionType(id={self.id}, name='{self.name}')>"
