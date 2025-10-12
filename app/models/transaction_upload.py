"""
Transaction Upload model for linking transactions to bulk uploads
"""
from sqlalchemy import String, Column, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel


class TransactionUpload(BaseModel):
    """
    Links transactions to their source bulk upload.
    Provides traceability for manually uploaded transactions.
    """
    __tablename__ = "transaction_uploads"

    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True, unique=True)
    bulk_upload_id = Column(Integer, ForeignKey("bulk_uploads.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)  # Row number in the CSV file
    csv_row_data = Column(JSON, nullable=True)  # Original CSV row data for reference

    # Relationships
    transaction = relationship("Transaction")
    bulk_upload = relationship("BulkUpload", back_populates="transaction_uploads")

    def __repr__(self):
        return f"<TransactionUpload(transaction_id={self.transaction_id}, bulk_upload_id={self.bulk_upload_id}, row={self.row_number})>"
