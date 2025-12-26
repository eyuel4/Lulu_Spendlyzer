from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class LinkTokenRequest(BaseModel):
    """Request to create a Plaid Link token"""
    pass


class LinkTokenResponse(BaseModel):
    """Response containing Plaid Link token"""
    link_token: str
    expiration: str


class PublicTokenExchange(BaseModel):
    """Request to exchange public token for access token"""
    public_token: str
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    accounts: Optional[List[dict]] = None


class PlaidAccountResponse(BaseModel):
    """Response for a connected Plaid account"""
    id: int
    bank_name: str
    card_name: str
    last4: str
    plaid_item_id: Optional[str] = None
    plaid_institution_id: Optional[str] = None
    last_sync_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlaidSyncResponse(BaseModel):
    """Response after syncing transactions"""
    success: bool
    message: str
    transactions_added: int
    transactions_updated: int
    card_id: int
    sync_date: datetime


class PlaidTransactionResponse(BaseModel):
    """Individual Plaid transaction"""
    transaction_id: str
    name: str
    merchant_name: Optional[str] = None
    amount: float
    date: date
    category: Optional[List[str]] = None
    pending: bool


class PlaidDisconnectResponse(BaseModel):
    """Response after disconnecting a Plaid account"""
    success: bool
    message: str
    card_id: int


class PlaidWebhookRequest(BaseModel):
    """Plaid webhook event request"""
    webhook_type: str
    webhook_code: str
    item_id: str
    error: Optional[dict] = None

