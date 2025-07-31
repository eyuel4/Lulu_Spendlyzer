from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.cache import get_cache, RedisCache
from app.services.transaction_service import TransactionService
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
from app.models.user import User as UserModel
from sqlalchemy import select
import jwt
import os
from typing import List, Optional

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
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """List transactions with caching."""
    try:
        transaction_service = TransactionService(cache)
        return await transaction_service.list_transactions(user_id, db, skip, limit, month)
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