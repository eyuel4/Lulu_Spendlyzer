"""
Budget Type model for categorizing transactions by budget classification
(Essential, Discretionary, Investment, Emergency)
"""
from sqlalchemy import String, Column, Integer, Text, Boolean
from .base import BaseModel


class BudgetType(BaseModel):
    """
    Represents budget type classifications for transactions.
    System-wide metadata that applies to all users.
    """
    __tablename__ = "budget_types"

    name = Column(String(50), unique=True, nullable=False, index=True)  # Essential, Discretionary, Investment, Emergency
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)  # Icon name/SVG path for UI
    color = Column(String(20), nullable=True)  # Color code for UI (e.g., 'text-green-600')
    is_active = Column(Boolean, default=True, index=True)
    display_order = Column(Integer, default=0)  # For ordering in UI

    def __repr__(self):
        return f"<BudgetType(id={self.id}, name='{self.name}')>"
