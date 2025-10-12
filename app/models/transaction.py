from sqlalchemy import String, Column, Integer, Float, Date, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from .base import BaseModel


class Transaction(BaseModel):
    __tablename__ = "transactions"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    plaid_transaction_id = Column(String, unique=True, nullable=True)  # NULL for manual transactions
    name = Column(String, nullable=False)
    merchant_name = Column(String, nullable=True)
    date = Column(Date, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    plaid_category = Column(String, nullable=True)
    custom_category = Column(String, nullable=True)
    budget_type = Column(String, nullable=True)
    month_id = Column(String, nullable=False, index=True)

    # New fields for manual transactions support
    transaction_type_id = Column(Integer, ForeignKey("transaction_types.id"), nullable=True)  # Income, Expense, Transfer, etc.
    expense_category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True)  # Detailed category
    expense_subcategory_id = Column(Integer, ForeignKey("expense_subcategories.id"), nullable=True)  # Subcategory
    payment_method_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=True)  # Payment method
    budget_type_id = Column(Integer, ForeignKey("budget_types.id"), nullable=True)  # Budget classification

    # Manual transaction tracking
    is_manual = Column(Boolean, default=False, index=True)  # True for manually entered transactions
    currency = Column(String(3), default="USD", nullable=False)  # USD or CAD
    is_shared = Column(Boolean, default=False, index=True)  # Visible to family group members
    notes = Column(String(500), nullable=True)

    # Relationships
    user = relationship("User", back_populates="transactions")
    card = relationship("Card", back_populates="transactions")
    transaction_type = relationship("TransactionType")
    expense_category = relationship("ExpenseCategory")
    expense_subcategory = relationship("ExpenseSubcategory")
    payment_method = relationship("PaymentMethod")
    budget_type_obj = relationship("BudgetType")

    # Indexes for common query patterns
    __table_args__ = (
        Index('idx_transaction_user_date', 'user_id', 'date'),
        Index('idx_transaction_user_month', 'user_id', 'month_id'),
        Index('idx_transaction_is_manual_user', 'is_manual', 'user_id'),
        Index('idx_transaction_is_shared_user', 'is_shared', 'user_id'),
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, date={self.date}, is_manual={self.is_manual})>"
