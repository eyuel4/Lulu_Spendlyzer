"""
Expense Subcategory model for detailed expense categorization
(Groceries, Restaurants, Gas, etc.)
"""
from sqlalchemy import String, Column, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel


class ExpenseSubcategory(BaseModel):
    """
    Represents subcategories under main expense categories.
    System-wide metadata that applies to all users.
    """
    __tablename__ = "expense_subcategories"

    name = Column(String(100), nullable=False, index=True)  # Groceries, Restaurants, Gas, etc.
    expense_category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)  # Icon name/SVG path for UI
    is_active = Column(Boolean, default=True, index=True)
    display_order = Column(Integer, default=0)  # For ordering in UI

    # Relationship
    category = relationship("ExpenseCategory")

    def __repr__(self):
        return f"<ExpenseSubcategory(id={self.id}, name='{self.name}', category_id={self.expense_category_id})>"
