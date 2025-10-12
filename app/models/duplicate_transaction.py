"""
Duplicate Transaction model for tracking potential duplicates identified during bulk uploads
"""
from sqlalchemy import String, Column, Integer, ForeignKey, Date, Float, JSON, DateTime, func
from sqlalchemy.orm import relationship
from .base import BaseModel


class DuplicateTransaction(BaseModel):
    """
    Tracks potential duplicate transactions identified during bulk upload processing.
    Allows users to review and accept/reject duplicates before final insertion.
    """
    __tablename__ = "duplicate_transactions"

    bulk_upload_id = Column(Integer, ForeignKey("bulk_uploads.id"), nullable=False, index=True)
    existing_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)  # Matching existing transaction

    # Duplicate transaction details
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    payment_method = Column(String(50), nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    description = Column(String(255), nullable=True)
    merchant = Column(String(255), nullable=True)

    # Similarity metrics
    similarity_score = Column(Float, default=0.0)  # 0-1 score indicating how similar to existing
    matching_fields = Column(JSON, nullable=True)  # Which fields match (date, amount, category, etc.)

    # User action
    user_action = Column(String(20), nullable=True, index=True)  # 'ACCEPTED', 'REJECTED', 'PENDING'
    user_notes = Column(String(500), nullable=True)

    # Timestamps
    identified_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    bulk_upload = relationship("BulkUpload", back_populates="duplicate_transactions")
    existing_transaction = relationship("Transaction")

    def __repr__(self):
        return f"<DuplicateTransaction(id={self.id}, bulk_upload_id={self.bulk_upload_id}, status='{self.user_action}')>"
