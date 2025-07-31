from sqlalchemy import String, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class Card(BaseModel):
    __tablename__ = "cards"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bank_name = Column(String, nullable=False)
    card_name = Column(String, nullable=False)
    last4 = Column(String(4), nullable=False)
    access_token = Column(String, nullable=False)

    user = relationship("User", back_populates="cards")
    transactions = relationship("Transaction", back_populates="card", cascade="all, delete-orphan") 