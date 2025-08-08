from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel
from datetime import datetime, timedelta

class TrustedDevice(BaseModel):
    __tablename__ = "trusted_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_hash = Column(String(64), nullable=False, index=True)
    token_hash = Column(String(128), nullable=False, index=True)
    device_name = Column(String(100), nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    location = Column(String(100), nullable=True)
    country_code = Column(String(3), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)

    user = relationship("User", back_populates="trusted_devices")
    sessions = relationship("UserSession", back_populates="trusted_device")

    def is_expired(self) -> bool:
        """Check if the trusted device token has expired"""
        return datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """Check if the trusted device is valid and not expired"""
        return self.is_active and not self.is_expired()

    @classmethod
    def create_expiration_date(cls, days: int = 7) -> datetime:
        """Create expiration date for trusted device"""
        return datetime.now() + timedelta(days=days) 