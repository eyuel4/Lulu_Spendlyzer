from sqlalchemy import String, Column, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class Card(BaseModel):
    __tablename__ = "cards"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bank_name = Column(String, nullable=False)
    card_name = Column(String, nullable=False)
    last4 = Column(String(4), nullable=False)
    access_token = Column(String, nullable=False)
    
    # Plaid integration fields
    plaid_item_id = Column(String, nullable=True)  # Plaid item ID for webhook tracking
    plaid_institution_id = Column(String, nullable=True)  # Plaid institution identifier
    last_sync_date = Column(DateTime, nullable=True)  # Track last transaction sync
    sync_enabled = Column(Boolean, default=True, nullable=False)  # Control automatic syncing

    user = relationship("User", back_populates="cards")
    transactions = relationship("Transaction", back_populates="card", cascade="all, delete-orphan") 