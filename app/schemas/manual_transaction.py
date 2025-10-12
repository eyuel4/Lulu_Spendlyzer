"""
Schemas for manual transaction operations
Includes single transaction, bulk upload, and duplicate handling
"""
from pydantic import BaseModel, ConfigDict, Field, validator
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal


class MetadataResponse(BaseModel):
    """Response model for metadata items"""
    id: int
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    bg_color: Optional[str] = None
    display_order: Optional[int] = None


class ManualTransactionBase(BaseModel):
    """Base schema for manual transactions"""
    date: date = Field(..., description="Transaction date (cannot be in the future)")
    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    currency: str = Field(default="USD", description="USD or CAD")
    description: str = Field(..., min_length=1, max_length=255, description="Transaction description")
    merchant: Optional[str] = Field(None, max_length=255, description="Merchant name")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")

    # Category & Type information
    transaction_type_id: int = Field(..., description="Transaction type ID (Income, Expense, etc.)")
    expense_category_id: Optional[int] = Field(None, description="Expense category ID")
    expense_subcategory_id: Optional[int] = Field(None, description="Expense subcategory ID")
    payment_method_id: int = Field(..., description="Payment method ID")
    budget_type_id: Optional[int] = Field(None, description="Budget type ID")

    # Card & Account information
    card_id: int = Field(..., description="Card ID associated with the transaction")
    is_shared: bool = Field(default=False, description="Whether to share with family group")

    @validator('date')
    def date_not_in_future(cls, v):
        """Validate that date is not in the future"""
        if v > date.today():
            raise ValueError('Transaction date cannot be in the future')
        return v

    @validator('date')
    def date_not_too_old(cls, v):
        """Validate that date is not more than 2 years old"""
        max_years_back = 2
        min_date = date.today().replace(year=date.today().year - max_years_back)
        if v < min_date:
            raise ValueError(f'Transaction date cannot be more than {max_years_back} years in the past')
        return v

    @validator('currency')
    def currency_validation(cls, v):
        """Validate currency is USD or CAD"""
        if v not in ['USD', 'CAD']:
            raise ValueError('Currency must be USD or CAD')
        return v


class ManualTransactionCreate(ManualTransactionBase):
    """Schema for creating a single manual transaction"""
    month_id: Optional[str] = Field(None, description="Month ID in format YYYY-MM (auto-calculated if not provided)")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2025-10-15",
                "amount": 45.99,
                "currency": "USD",
                "description": "Groceries",
                "merchant": "Whole Foods",
                "transaction_type_id": 1,
                "expense_category_id": 1,
                "expense_subcategory_id": 1,
                "payment_method_id": 1,
                "budget_type_id": 1,
                "card_id": 1,
                "is_shared": False,
                "notes": "Weekly grocery run"
            }
        }


class BulkTransactionCreateRequest(BaseModel):
    """Schema for bulk transaction creation from CSV"""
    transactions: List[ManualTransactionCreate] = Field(..., min_items=1, max_items=1000, description="List of transactions (max 1000)")
    filename: Optional[str] = Field(None, description="Original CSV filename for reference")
    allow_duplicates: bool = Field(default=False, description="Whether to allow duplicate transactions")


class ManualTransactionUpdate(BaseModel):
    """Schema for updating a manual transaction"""
    date: Optional[date] = None
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    description: Optional[str] = Field(None, min_length=1, max_length=255)
    merchant: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=500)
    transaction_type_id: Optional[int] = None
    expense_category_id: Optional[int] = None
    expense_subcategory_id: Optional[int] = None
    payment_method_id: Optional[int] = None
    budget_type_id: Optional[int] = None
    is_shared: Optional[bool] = None

    @validator('date')
    def date_not_in_future(cls, v):
        """Validate that date is not in the future"""
        if v and v > date.today():
            raise ValueError('Transaction date cannot be in the future')
        return v

    @validator('currency')
    def currency_validation(cls, v):
        """Validate currency is USD or CAD"""
        if v and v not in ['USD', 'CAD']:
            raise ValueError('Currency must be USD or CAD')
        return v


class ManualTransactionResponse(ManualTransactionBase):
    """Response schema for manual transactions"""
    id: int
    user_id: int
    month_id: str
    is_manual: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Relationship data
    expense_category: Optional[MetadataResponse] = None
    expense_subcategory: Optional[MetadataResponse] = None
    payment_method: Optional[MetadataResponse] = None
    transaction_type: Optional[MetadataResponse] = None
    budget_type: Optional[MetadataResponse] = None

    model_config = ConfigDict(from_attributes=True)


class DuplicateTransactionInfo(BaseModel):
    """Schema for duplicate transaction information"""
    duplicate_transaction_id: int
    existing_transaction_id: Optional[int] = None
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    matching_fields: List[str] = Field(..., description="Fields that matched (date, amount, category, etc.)")
    new_transaction: ManualTransactionResponse = Field(..., description="The duplicate transaction being added")
    existing_transaction: Optional[ManualTransactionResponse] = Field(None, description="The existing matching transaction")
    user_message: str = Field(..., description="Human-readable message about the duplicate")


class DuplicateConfirmationRequest(BaseModel):
    """Schema for confirming duplicate transaction handling"""
    duplicate_transaction_ids: List[int] = Field(..., min_items=1, description="IDs of duplicates to handle")
    action: str = Field(..., description="'ACCEPT' to keep duplicates, 'REJECT' to discard them")
    user_notes: Optional[str] = Field(None, max_length=500, description="User notes about the decision")


class BulkUploadResponse(BaseModel):
    """Response schema for bulk upload operations"""
    bulk_upload_id: int
    total_rows: int
    successful_count: int
    failed_count: int
    duplicate_count: int
    status: str
    error_message: Optional[str] = None
    created_transactions: List[ManualTransactionResponse] = Field(default_factory=list)
    duplicate_transactions: List[DuplicateTransactionInfo] = Field(default_factory=list)
    failed_rows: List[dict] = Field(default_factory=list, description="Details of failed row imports")


class BulkUploadStatusResponse(BaseModel):
    """Response schema for checking bulk upload status"""
    bulk_upload_id: int
    user_id: int
    filename: str
    total_rows: int
    successful_count: int
    failed_count: int
    duplicate_count: int
    status: str
    error_message: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionMetadataResponse(BaseModel):
    """Response schema for transaction metadata"""
    transaction_types: List[MetadataResponse]
    expense_categories: List[MetadataResponse]
    payment_methods: List[MetadataResponse]
    budget_types: List[MetadataResponse]


class TransactionListResponse(BaseModel):
    """Response schema for transaction list"""
    total: int
    skip: int
    limit: int
    transactions: List[ManualTransactionResponse]


class CSVUploadResponse(BaseModel):
    """Response schema for CSV upload initiation"""
    bulk_upload_id: int
    status: str
    message: str
    filename: str
