from sqlalchemy import String, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class CategoryOverride(BaseModel):
    __tablename__ = "category_overrides"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plaid_category = Column(String, nullable=False)
    merchant_name = Column(String, nullable=True)
    custom_category = Column(String, nullable=False)

    user = relationship("User", back_populates="category_overrides") 