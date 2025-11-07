"""
Expense Category model for categorizing expenses
(Food & Dining, Transportation, Shopping, etc.)
"""
from sqlalchemy import String, Column, Integer, Text, Boolean
from .base import BaseModel


class ExpenseCategory(BaseModel):
    """
    Represents expense categories for organizing transactions.
    System-wide metadata that applies to all users.
    """
    __tablename__ = "expense_categories"

    name = Column(String(100), unique=True, nullable=False, index=True)  # Food & Dining, Transportation, etc.
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)  # Icon name/SVG path for UI
    color = Column(String(20), nullable=True)  # Text color (e.g., 'text-orange-600')
    bg_color = Column(String(20), nullable=True)  # Background color (e.g., 'bg-orange-100')
    is_active = Column(Boolean, default=True, index=True)
    display_order = Column(Integer, default=0)  # For ordering in UI

    def __repr__(self):
        return f"<ExpenseCategory(id={self.id}, name='{self.name}')>"
