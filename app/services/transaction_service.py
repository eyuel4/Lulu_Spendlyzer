from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.models.transaction import Transaction
from app.models.user import User as UserModel
from app.core.cache import RedisCache, CacheKeys
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
import logging

logger = logging.getLogger(__name__)

class TransactionService:
    def __init__(self, cache: RedisCache):
        self.cache = cache

    async def create_transaction(
        self, 
        transaction_data: TransactionCreate, 
        user_id: int, 
        db: AsyncSession
    ) -> TransactionResponse:
        """Create a new transaction with cache invalidation"""
        try:
            # Create transaction
            transaction = Transaction(
                user_id=user_id,
                card_id=transaction_data.card_id,
                plaid_transaction_id=transaction_data.plaid_transaction_id,
                name=transaction_data.name,
                merchant_name=transaction_data.merchant_name,
                date=transaction_data.date,
                amount=transaction_data.amount,
                plaid_category=transaction_data.plaid_category,
                custom_category=transaction_data.custom_category,
                budget_type=transaction_data.budget_type,
                month_id=transaction_data.month_id
            )
            
            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)
            
            # Invalidate related caches
            await self._invalidate_user_transaction_caches(user_id, transaction_data.month_id)
            
            return TransactionResponse.from_orm(transaction)
            
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            await db.rollback()
            raise

    async def get_transaction(
        self, 
        transaction_id: int, 
        user_id: int, 
        db: AsyncSession
    ) -> Optional[TransactionResponse]:
        """Get a transaction by ID with caching"""
        cache_key = CacheKeys.transaction(transaction_id)
        
        # Try cache first
        cached_transaction = await self.cache.get(cache_key)
        if cached_transaction:
            logger.debug(f"Cache HIT: transaction {transaction_id}")
            return TransactionResponse(**cached_transaction)
        
        # Get from database
        result = await db.execute(
            select(Transaction)
            .where(and_(Transaction.id == transaction_id, Transaction.user_id == user_id))
            .options(selectinload(Transaction.user), selectinload(Transaction.card))
        )
        transaction = result.scalars().first()
        
        if not transaction:
            return None
        
        # Cache the result
        transaction_response = TransactionResponse.from_orm(transaction)
        await self.cache.set(cache_key, transaction_response.dict(), expire=1800)  # 30 minutes
        
        return transaction_response

    async def list_transactions(
        self, 
        user_id: int, 
        db: AsyncSession,
        skip: int = 0, 
        limit: int = 100,
        month: Optional[str] = None
    ) -> List[TransactionResponse]:
        """List transactions with caching"""
        cache_key = CacheKeys.transactions(user_id, month) if month else CacheKeys.transactions(user_id)
        
        # Try cache first
        cached_transactions = await self.cache.get(cache_key)
        if cached_transactions:
            logger.debug(f"Cache HIT: transactions for user {user_id}")
            # Apply pagination to cached results
            start = skip
            end = skip + limit
            return [TransactionResponse(**t) for t in cached_transactions[start:end]]
        
        # Build query
        query = select(Transaction).where(Transaction.user_id == user_id)
        
        if month:
            query = query.where(Transaction.month_id == month)
        
        query = query.options(selectinload(Transaction.user), selectinload(Transaction.card))
        query = query.offset(skip).limit(limit).order_by(Transaction.date.desc())
        
        result = await db.execute(query)
        transactions = result.scalars().all()
        
        # Convert to response models
        transaction_responses = [TransactionResponse.from_orm(t) for t in transactions]
        
        # Cache the full result (without pagination)
        if not month:
            # Cache all transactions for this user
            full_query = select(Transaction).where(Transaction.user_id == user_id)
            full_query = full_query.options(selectinload(Transaction.user), selectinload(Transaction.card))
            full_query = full_query.order_by(Transaction.date.desc())
            
            full_result = await db.execute(full_query)
            all_transactions = full_result.scalars().all()
            all_responses = [TransactionResponse.from_orm(t).dict() for t in all_transactions]
            await self.cache.set(cache_key, all_responses, expire=900)  # 15 minutes
        
        return transaction_responses

    async def update_transaction(
        self, 
        transaction_id: int, 
        transaction_data: TransactionUpdate, 
        user_id: int, 
        db: AsyncSession
    ) -> Optional[TransactionResponse]:
        """Update a transaction with cache invalidation"""
        try:
            # Get existing transaction
            result = await db.execute(
                select(Transaction)
                .where(and_(Transaction.id == transaction_id, Transaction.user_id == user_id))
            )
            transaction = result.scalars().first()
            
            if not transaction:
                return None
            
            # Update fields
            update_data = transaction_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(transaction, field, value)
            
            await db.commit()
            await db.refresh(transaction)
            
            # Invalidate caches
            await self.cache.delete(CacheKeys.transaction(transaction_id))
            await self._invalidate_user_transaction_caches(user_id, str(transaction.month_id))
            
            return TransactionResponse.from_orm(transaction)
            
        except Exception as e:
            logger.error(f"Error updating transaction: {e}")
            await db.rollback()
            raise

    async def delete_transaction(
        self, 
        transaction_id: int, 
        user_id: int, 
        db: AsyncSession
    ) -> bool:
        """Delete a transaction with cache invalidation"""
        try:
            # Get transaction to know its month_id for cache invalidation
            result = await db.execute(
                select(Transaction)
                .where(and_(Transaction.id == transaction_id, Transaction.user_id == user_id))
            )
            transaction = result.scalars().first()
            
            if not transaction:
                return False
            
            month_id = str(transaction.month_id)
            
            # Delete transaction
            await db.delete(transaction)
            await db.commit()
            
            # Invalidate caches
            await self.cache.delete(CacheKeys.transaction(transaction_id))
            await self._invalidate_user_transaction_caches(user_id, month_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            await db.rollback()
            raise

    async def get_transaction_summary(
        self, 
        user_id: int, 
        db: AsyncSession,
        month: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get transaction summary with caching"""
        cache_key = f"transaction_summary:{user_id}:{month}" if month else f"transaction_summary:{user_id}"
        
        # Try cache first
        cached_summary = await self.cache.get(cache_key)
        if cached_summary:
            logger.debug(f"Cache HIT: transaction summary for user {user_id}")
            return cached_summary
        
        # Build query
        query = select(
            func.count(Transaction.id).label('total_transactions'),
            func.sum(Transaction.amount).label('total_amount'),
            func.avg(Transaction.amount).label('average_amount'),
            func.min(Transaction.amount).label('min_amount'),
            func.max(Transaction.amount).label('max_amount')
        ).where(Transaction.user_id == user_id)
        
        if month:
            query = query.where(Transaction.month_id == month)
        
        result = await db.execute(query)
        summary = result.first()
        
        if summary:
            summary_data = {
                'total_transactions': summary.total_transactions or 0,
                'total_amount': float(summary.total_amount or 0),
                'average_amount': float(summary.average_amount or 0),
                'min_amount': float(summary.min_amount or 0),
                'max_amount': float(summary.max_amount or 0),
                'month': month
            }
        else:
            summary_data = {
                'total_transactions': 0,
                'total_amount': 0.0,
                'average_amount': 0.0,
                'min_amount': 0.0,
                'max_amount': 0.0,
                'month': month
            }
        
        # Cache the summary
        await self.cache.set(cache_key, summary_data, expire=1800)  # 30 minutes
        
        return summary_data

    async def get_transactions_by_category(
        self, 
        user_id: int, 
        db: AsyncSession,
        month: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get transactions grouped by category with caching"""
        cache_key = f"transactions_by_category:{user_id}:{month}" if month else f"transactions_by_category:{user_id}"
        
        # Try cache first
        cached_categories = await self.cache.get(cache_key)
        if cached_categories:
            logger.debug(f"Cache HIT: transactions by category for user {user_id}")
            return cached_categories
        
        # Build query
        query = select(
            Transaction.plaid_category,
            Transaction.custom_category,
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount).label('total_amount')
        ).where(Transaction.user_id == user_id)
        
        if month:
            query = query.where(Transaction.month_id == month)
        
        query = query.group_by(Transaction.plaid_category, Transaction.custom_category)
        
        result = await db.execute(query)
        categories = result.all()
        
        category_data = {}
        for cat in categories:
            category_name = cat.custom_category or cat.plaid_category or 'Uncategorized'
            if category_name not in category_data:
                category_data[category_name] = {
                    'count': 0,
                    'total_amount': 0.0
                }
            category_data[category_name]['count'] += cat.count
            category_data[category_name]['total_amount'] += float(cat.total_amount or 0)
        
        # Cache the category data
        await self.cache.set(cache_key, category_data, expire=1800)  # 30 minutes
        
        return category_data

    async def _invalidate_user_transaction_caches(self, user_id: int, month_id: Optional[str] = None):
        """Invalidate all transaction-related caches for a user"""
        try:
            # Delete specific caches
            await self.cache.delete_pattern(f"transactions:{user_id}:*")
            await self.cache.delete_pattern(f"transaction_summary:{user_id}:*")
            await self.cache.delete_pattern(f"transactions_by_category:{user_id}:*")
            
            if month_id:
                await self.cache.delete(f"transactions:{user_id}:{month_id}")
                await self.cache.delete(f"transaction_summary:{user_id}:{month_id}")
                await self.cache.delete(f"transactions_by_category:{user_id}:{month_id}")
            
            logger.debug(f"Invalidated transaction caches for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error invalidating transaction caches: {e}")

# Transaction cache keys are now defined in CacheKeys class 