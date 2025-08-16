from sqlalchemy import String, Column, Boolean, ForeignKey, Integer, DateTime, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel
from .system_log import AuditLog

class User(BaseModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_primary = Column(Boolean, default=True)
    family_group_id = Column(Integer, ForeignKey('family_groups.id', use_alter=True), nullable=True)
    auth_provider = Column(String, nullable=False, default='local')  # 'local' or 'google'
    provider_id = Column(String, nullable=True, unique=True)  # Google user ID
    avatar_url = Column(String, nullable=True)  # Google profile picture URL
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    token_version = Column(Integer, default=0, nullable=False)

    cards = relationship("Card", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    category_overrides = relationship("CategoryOverride", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    grocery_categories = relationship("GroceryCategory", back_populates="user", cascade="all, delete-orphan")
    shopping_categories = relationship("ShoppingCategory", back_populates="user", cascade="all, delete-orphan")
    family_group = relationship('FamilyGroup', back_populates='users', foreign_keys=[family_group_id])
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    system_logs = relationship("SystemLog", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys=[AuditLog.user_id]
    )
    performed_audit_logs = relationship(
        "AuditLog",
        back_populates="performer",
        cascade="all, delete-orphan",
        foreign_keys=[AuditLog.performed_by]
    )
    feature_requests = relationship("FeatureRequest", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    trusted_devices = relationship("TrustedDevice", back_populates="user", cascade="all, delete-orphan")
    two_factor_auth = relationship("TwoFactorAuth", back_populates="user", uselist=False, cascade="all,delete-orphan")
    notification_settings = relationship("NotificationSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    privacy_settings = relationship("PrivacySettings", back_populates="user", uselist=False, cascade="all, delete-orphan")

class UserPreferences(BaseModel):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    account_type = Column(String, nullable=False)  # 'personal' or 'family'
    primary_goal = Column(JSON, nullable=False)  # List of goals as JSON
    financial_focus = Column(JSON, nullable=False)  # List of focus areas as JSON
    experience_level = Column(String, nullable=False)  # 'beginner', 'intermediate', 'advanced'
    default_transaction_method = Column(String(50), nullable=True)  # 'bank-api', 'upload-statement', 'manual'
    theme = Column(String(20), default='light')  # 'light', 'dark'
    notifications = Column(JSON, default={
        'email': True,
        'push': True,
        'sms': False
    })
    date_format = Column(String(20), default='MM/DD/YYYY')
    currency = Column(String(10), default='USD')
    
    user = relationship("User", back_populates="preferences")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_type': self.account_type,
            'primary_goal': self.primary_goal,
            'financial_focus': self.financial_focus,
            'experience_level': self.experience_level,
            'defaultTransactionMethod': self.default_transaction_method,
            'theme': self.theme,
            'notifications': self.notifications,
            'dateFormat': self.date_format,
            'currency': self.currency,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 