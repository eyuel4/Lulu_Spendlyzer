"""
Bulk Upload model for tracking CSV transaction uploads
"""
from sqlalchemy import String, Column, Integer, ForeignKey, DateTime, JSON, Boolean, Text, func
from sqlalchemy.orm import relationship
from .base import BaseModel


class BulkUpload(BaseModel):
    """
    Tracks bulk transaction uploads from CSV files.
    Provides audit trail and upload history for users.
    """
    __tablename__ = "bulk_uploads"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    total_rows = Column(Integer, nullable=False)  # Total rows in CSV
    successful_count = Column(Integer, default=0)  # Successfully inserted
    failed_count = Column(Integer, default=0)  # Failed to insert
    duplicate_count = Column(Integer, default=0)  # Duplicates identified
    status = Column(String(20), nullable=False, index=True)  # 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
    error_message = Column(Text, nullable=True)  # Error details if FAILED
    metadata = Column(JSON, nullable=True)  # Additional metadata (date range, categories used, etc.)

    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")
    duplicate_transactions = relationship("DuplicateTransaction", back_populates="bulk_upload", cascade="all, delete-orphan")
    transaction_uploads = relationship("TransactionUpload", back_populates="bulk_upload", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BulkUpload(id={self.id}, user_id={self.user_id}, filename='{self.filename}', status='{self.status}')>"
