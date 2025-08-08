from sqlalchemy import Column, Integer, Boolean, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models.base import Base


class PrivacySettings(Base):
    __tablename__ = "privacy_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Privacy preferences
    profile_visibility = Column(String, default="private")  # 'private' | 'family' | 'public'
    data_sharing = Column(Boolean, default=False)
    analytics_sharing = Column(Boolean, default=True)
    allow_family_access = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship
    user = relationship("User", back_populates="privacy_settings")
    
    def __repr__(self):
        return f"<PrivacySettings(user_id={self.user_id})>"
