from sqlalchemy import String, Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel

class GroceryCategory(BaseModel):
    __tablename__ = "grocery_categories"
    __table_args__ = (UniqueConstraint('user_id', 'store_name', name='uix_user_store'),)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    store_name = Column(String, nullable=False)

    user = relationship("User", back_populates="grocery_categories") 