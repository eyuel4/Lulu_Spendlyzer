from sqlalchemy import String, Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel

class ShoppingCategory(BaseModel):
    __tablename__ = "shopping_categories"
    __table_args__ = (UniqueConstraint('user_id', 'category_name', name='uix_user_category'),)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_name = Column(String, nullable=False)

    user = relationship("User", back_populates="shopping_categories") 