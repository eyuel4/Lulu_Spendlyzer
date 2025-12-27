from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.cache import get_cache, RedisCache
from app.services.transaction_service import TransactionService
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
from app.models.user import User as UserModel
from sqlalchemy import select, distinct
import jwt
import os
from typing import List, Optional
from datetime import date
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"

async def get_current_user_id(request: Request, db: AsyncSession = Depends(get_db)) -> int:
    """Get current user ID from JWT token"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        user_id = int(payload.get("sub"))
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

@router.post("/", response_model=TransactionResponse)
async def create_transaction(
    transaction: TransactionCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """Create a new transaction with caching."""
    try:
        transaction_service = TransactionService(cache)
        return await transaction_service.create_transaction(transaction, user_id, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[TransactionResponse])
async def list_transactions(
    skip: int = 0,
    limit: int = 100,
    month: Optional[str] = None,
    card_id: Optional[int] = Query(None, description="Filter by card ID"),
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
    merchant_name: Optional[str] = Query(None, description="Filter by merchant name"),
    expense_category_id: Optional[int] = Query(None, description="Filter by expense category ID"),
    custom_category: Optional[str] = Query(None, description="Filter by custom category"),
    start_date: Optional[date] = Query(None, description="Start date for date range filter"),
    end_date: Optional[date] = Query(None, description="End date for date range filter"),
    currency: Optional[str] = Query(None, description="Filter by currency (USD/CAD)"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """List transactions with filtering and caching."""
    try:
        transaction_service = TransactionService(cache)
        return await transaction_service.list_transactions(
            user_id, db, skip, limit, month,
            card_id=card_id,
            bank_name=bank_name,
            merchant_name=merchant_name,
            expense_category_id=expense_category_id,
            custom_category=custom_category,
            start_date=start_date,
            end_date=end_date,
            currency=currency
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """Get a transaction by ID with caching."""
    try:
        transaction_service = TransactionService(cache)
        transaction = await transaction_service.get_transaction(transaction_id, user_id, db)
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return transaction
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    transaction: TransactionUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """Update a transaction with cache invalidation."""
    try:
        transaction_service = TransactionService(cache)
        updated_transaction = await transaction_service.update_transaction(
            transaction_id, transaction, user_id, db
        )
        
        if not updated_transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return updated_transaction
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """Delete a transaction with cache invalidation."""
    try:
        transaction_service = TransactionService(cache)
        success = await transaction_service.delete_transaction(transaction_id, user_id, db)
        
        if not success:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return {"message": "Transaction deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/summary/")
async def get_transaction_summary(
    month: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """Get transaction summary with caching."""
    try:
        transaction_service = TransactionService(cache)
        return await transaction_service.get_transaction_summary(user_id, db, month)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/by-category/")
async def get_transactions_by_category(
    month: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """Get transactions grouped by category with caching."""
    try:
        transaction_service = TransactionService(cache)
        return await transaction_service.get_transactions_by_category(user_id, db, month)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/dropdown-metadata/")
async def get_dropdown_metadata(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """
    Get dropdown metadata for transaction editing
    Returns unique merchants, banks, cards, categories, and custom categories for the user
    """
    try:
        from app.models.transaction import Transaction
        from app.models.card import Card
        from app.models.expense_category import ExpenseCategory
        from sqlalchemy import distinct, func
        
        cache_key = f"transaction_dropdown_metadata:{user_id}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # Get unique merchants
        merchant_result = await db.execute(
            select(distinct(Transaction.merchant_name))
            .where(Transaction.user_id == user_id, Transaction.merchant_name.isnot(None))
            .order_by(Transaction.merchant_name)
        )
        merchants = [m[0] for m in merchant_result.all() if m[0]]
        
        # Get unique custom categories
        custom_cat_result = await db.execute(
            select(distinct(Transaction.custom_category))
            .where(Transaction.user_id == user_id, Transaction.custom_category.isnot(None))
            .order_by(Transaction.custom_category)
        )
        custom_categories = [c[0] for c in custom_cat_result.all() if c[0]]
        
        # Get user's banks and cards
        cards_result = await db.execute(
            select(Card).where(Card.user_id == user_id).order_by(Card.bank_name, Card.card_name)
        )
        cards = cards_result.scalars().all()
        
        banks = []
        cards_list = []
        seen_banks = set()
        
        for card in cards:
            if card.bank_name not in seen_banks:
                banks.append({
                    "id": card.id,  # Using card id as bank identifier
                    "name": card.bank_name
                })
                seen_banks.add(card.bank_name)
            
            cards_list.append({
                "id": card.id,
                "name": card.card_name,
                "bank_name": card.bank_name,
                "last4": card.last4
            })
        
        # Get expense categories
        categories_result = await db.execute(
            select(ExpenseCategory).where(ExpenseCategory.is_active == True).order_by(ExpenseCategory.display_order, ExpenseCategory.name)
        )
        categories = categories_result.scalars().all()
        
        metadata = {
            "merchants": merchants,
            "banks": banks,
            "cards": cards_list,
            "expense_categories": [
                {
                    "id": cat.id,
                    "name": cat.name,
                    "description": cat.description
                }
                for cat in categories
            ],
            "custom_categories": custom_categories
        }
        
        # Cache for 30 minutes
        await cache.set(cache_key, metadata, expire=1800)
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error fetching dropdown metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dropdown metadata") 