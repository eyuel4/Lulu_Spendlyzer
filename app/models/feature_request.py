from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel
from sqlalchemy.sql import func

class FeatureRequest(BaseModel):
    __tablename__ = "feature_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    description = Column(Text, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # 'pending', 'reviewed', etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="feature_requests") 