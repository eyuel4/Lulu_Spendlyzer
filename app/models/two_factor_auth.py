from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel

class TwoFactorAuth(BaseModel):
    __tablename__ = "two_factor_auth"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    is_enabled = Column(Boolean, default=False, nullable=False)
    method = Column(String(20), nullable=False, default='authenticator')  # 'authenticator', 'sms', 'email'
    secret_key = Column(String(32), nullable=True)  # Base32 secret for TOTP
    phone_number = Column(String(20), nullable=True)  # For SMS 2FA
    backup_codes = Column(Text, nullable=True)  # JSON array of backup codes
    temp_code = Column(String(6), nullable=True)  # Temporary SMS/Email verification code
    temp_code_expires_at = Column(DateTime(timezone=True), nullable=True)  # Expiration time for temp code
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="two_factor_auth")

class TwoFactorBackupCode(BaseModel):
    __tablename__ = "two_factor_backup_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code_hash = Column(String(128), nullable=False)  # Hashed backup code
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")