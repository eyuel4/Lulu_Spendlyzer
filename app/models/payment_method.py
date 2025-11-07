"""
Payment Method model for categorizing payment types
(Credit Card, Debit Card, Cash, Check, Bank Transfer, Wire, etc.)
"""
from sqlalchemy import String, Column, Integer, Text, Boolean
from .base import BaseModel


class PaymentMethod(BaseModel):
    """
    Represents different payment methods used for transactions.
    System-wide metadata that applies to all users.
    """
    __tablename__ = "payment_methods"

    name = Column(String(50), unique=True, nullable=False, index=True)  # Credit Card, Debit Card, Cash, Check, etc.
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)  # Icon name/SVG path for UI
    color = Column(String(20), nullable=True)  # Color code for UI (e.g., 'text-blue-600')
    is_active = Column(Boolean, default=True, index=True)
    display_order = Column(Integer, default=0)  # For ordering in UI

    def __repr__(self):
        return f"<PaymentMethod(id={self.id}, name='{self.name}')>"
