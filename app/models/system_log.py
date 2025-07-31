from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class SystemLog(Base):
    """
    System Log model for storing application errors, warnings, and audit events
    with comprehensive metadata for debugging and monitoring.
    """
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Log classification
    level = Column(String(20), nullable=False, index=True)  # 'ERROR', 'WARNING', 'INFO', 'DEBUG'
    category = Column(String(50), nullable=False, index=True)  # 'AUTH', 'EMAIL', 'DATABASE', 'API', 'SYSTEM'
    source = Column(String(100), nullable=False)  # Component/service name
    
    # Error details
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    error_type = Column(String(100))  # Exception class name
    error_details = Column(Text)  # Full error details/stack trace
    
    # Context information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Associated user (if applicable)
    session_id = Column(String(100))  # Session identifier
    request_id = Column(String(100))  # Request identifier for tracing
    endpoint = Column(String(200))  # API endpoint (if applicable)
    method = Column(String(10))  # HTTP method (if applicable)
    
    # System context
    ip_address = Column(String(45))  # Client IP address
    user_agent = Column(String(500))  # User agent string
    environment = Column(String(20), default='development')  # Environment (dev, staging, prod)
    
    # Additional metadata
    meta = Column(JSON)  # Additional structured data
    tags = Column(JSON)  # Tags for categorization and filtering
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="system_logs")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_system_logs_level_category', 'level', 'category'),
        Index('idx_system_logs_created_at', 'created_at'),
        Index('idx_system_logs_user_created', 'user_id', 'created_at'),
        Index('idx_system_logs_source_level', 'source', 'level'),
    )

    def __repr__(self):
        return f"<SystemLog(id={self.id}, level='{self.level}', category='{self.category}', source='{self.source}')>"


class AuditLog(Base):
    """
    Audit Log model for tracking user actions and system events
    for compliance and security monitoring.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Event classification
    event_type = Column(String(50), nullable=False, index=True)  # 'LOGIN', 'LOGOUT', 'CREATE', 'UPDATE', 'DELETE', 'VIEW'
    resource_type = Column(String(50), nullable=False, index=True)  # 'USER', 'TRANSACTION', 'CARD', 'REPORT', etc.
    resource_id = Column(String(100))  # ID of the affected resource
    
    # User context
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Who performed the action
    
    # Action details
    action = Column(String(200), nullable=False)  # Human-readable action description
    details = Column(Text)  # Detailed description of the action
    changes = Column(JSON)  # Before/after data for updates
    
    # System context
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    session_id = Column(String(100))
    request_id = Column(String(100))
    
    # Security context
    is_successful = Column(String(10), default='SUCCESS')  # 'SUCCESS', 'FAILURE', 'PARTIAL'
    failure_reason = Column(Text)  # Reason for failure (if applicable)
    
    # Additional metadata
    meta = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="audit_logs")
    performer = relationship("User", foreign_keys=[performed_by], back_populates="performed_audit_logs")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_audit_logs_event_type', 'event_type'),
        Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_logs_user_created', 'user_id', 'created_at'),
        Index('idx_audit_logs_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type='{self.event_type}', resource_type='{self.resource_type}', user_id={self.user_id})>" 