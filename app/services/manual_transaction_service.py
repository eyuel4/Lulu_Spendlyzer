"""
Manual Transaction Service
Handles creation, update, deletion, and bulk upload of manually entered transactions
Includes duplicate detection and audit logging
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.models.transaction import Transaction
from app.models.bulk_upload import BulkUpload
from app.models.duplicate_transaction import DuplicateTransaction
from app.models.transaction_upload import TransactionUpload
from app.models.card import Card
from app.schemas.manual_transaction import (
    ManualTransactionCreate, ManualTransactionUpdate, ManualTransactionResponse,
    BulkUploadResponse, BulkTransactionCreateRequest, DuplicateTransactionInfo
)
from app.core.cache import RedisCache, CacheKeys
from app.services.logging_service import logging_service

logger = logging.getLogger(__name__)


class ManualTransactionService:
    """Service for managing manual transactions"""

    def __init__(self, cache: RedisCache):
        self.cache = cache
        self.DUPLICATE_SIMILARITY_THRESHOLD = 0.85  # 85% match threshold for duplicates

    async def create_manual_transaction(
        self,
        transaction_data: ManualTransactionCreate,
        user_id: int,
        card_id: int,
        db: AsyncSession,
        is_shared: bool = False
    ) -> ManualTransactionResponse:
        """
        Create a single manual transaction

        Args:
            transaction_data: Transaction details
            user_id: User ID
            card_id: Card ID
            db: Database session
            is_shared: Whether transaction is shared with family

        Returns:
            ManualTransactionResponse
        """
        try:
            # Auto-calculate month_id if not provided
            month_id = transaction_data.month_id or transaction_data.date.strftime("%Y-%m")

            # Generate unique plaid_transaction_id for manual transactions
            plaid_transaction_id = f"MANUAL_{user_id}_{int(datetime.now().timestamp() * 1000)}"

            transaction = Transaction(
                user_id=user_id,
                card_id=card_id,
                plaid_transaction_id=plaid_transaction_id,
                name=transaction_data.description,
                merchant_name=transaction_data.merchant,
                date=transaction_data.date,
                amount=transaction_data.amount,
                month_id=month_id,
                is_manual=True,
                currency=transaction_data.currency,
                is_shared=is_shared,
                notes=transaction_data.notes,
                transaction_type_id=transaction_data.transaction_type_id,
                expense_category_id=transaction_data.expense_category_id,
                expense_subcategory_id=transaction_data.expense_subcategory_id,
                payment_method_id=transaction_data.payment_method_id,
                budget_type_id=transaction_data.budget_type_id,
            )

            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)

            # Audit log
            await logging_service.audit_log(
                event_type="CREATE",
                resource_type="TRANSACTION",
                resource_id=str(transaction.id),
                user_id=user_id,
                action=f"Created manual transaction: {transaction.name}",
                is_successful="SUCCESS"
            )

            # Invalidate caches
            await self._invalidate_user_transaction_caches(user_id, month_id)

            return ManualTransactionResponse.from_orm(transaction)

        except Exception as e:
            logger.error(f"Error creating manual transaction: {e}")
            await db.rollback()

            await logging_service.audit_log(
                event_type="CREATE",
                resource_type="TRANSACTION",
                user_id=user_id,
                action="Failed to create manual transaction",
                is_successful="FAILURE",
                meta={"error": str(e)}
            )
            raise

    async def create_bulk_transactions(
        self,
        bulk_request: BulkTransactionCreateRequest,
        user_id: int,
        db: AsyncSession,
        check_duplicates: bool = True
    ) -> BulkUploadResponse:
        """
        Create multiple transactions from bulk upload
        Checks for duplicates and returns report

        Args:
            bulk_request: Bulk transaction request
            user_id: User ID
            db: Database session
            check_duplicates: Whether to check for duplicates

        Returns:
            BulkUploadResponse with results and any duplicates found
        """
        try:
            # Create bulk upload record
            bulk_upload = BulkUpload(
                user_id=user_id,
                filename=bulk_request.filename or "bulk_upload.csv",
                total_rows=len(bulk_request.transactions),
                status="PROCESSING",
                metadata={}
            )
            db.add(bulk_upload)
            await db.commit()
            await db.refresh(bulk_upload)

            logger.info(f"Starting bulk upload {bulk_upload.id} for user {user_id} with {len(bulk_request.transactions)} transactions")

            created_transactions: List[ManualTransactionResponse] = []
            duplicate_info: List[DuplicateTransactionInfo] = []
            failed_rows: List[Dict[str, Any]] = []
            duplicate_ids: List[int] = []

            for idx, trans_data in enumerate(bulk_request.transactions, 1):
                try:
                    # Verify card exists and belongs to user
                    card_result = await db.execute(
                        select(Card).where(and_(Card.id == trans_data.card_id, Card.user_id == user_id))
                    )
                    if not card_result.scalars().first():
                        failed_rows.append({
                            "row": idx,
                            "error": f"Card {trans_data.card_id} not found or doesn't belong to user"
                        })
                        continue

                    # Check for duplicates if enabled
                    if check_duplicates and not bulk_request.allow_duplicates:
                        duplicates = await self._find_duplicates(
                            user_id, trans_data.card_id, trans_data.date,
                            trans_data.amount, trans_data.expense_category_id, db
                        )

                        if duplicates:
                            for dup in duplicates:
                                # Create duplicate transaction record
                                month_id = trans_data.month_id or trans_data.date.strftime("%Y-%m")
                                plaid_id = f"MANUAL_{user_id}_{int(datetime.now().timestamp() * 1000)}"

                                dup_trans = DuplicateTransaction(
                                    bulk_upload_id=bulk_upload.id,
                                    existing_transaction_id=dup.id,
                                    date=trans_data.date,
                                    amount=trans_data.amount,
                                    category=trans_data.description,
                                    payment_method=str(trans_data.payment_method_id),
                                    card_id=trans_data.card_id,
                                    description=trans_data.description,
                                    merchant=trans_data.merchant,
                                    similarity_score=0.95,  # High similarity
                                    matching_fields=["date", "amount", "category"],
                                    user_action="PENDING"
                                )
                                db.add(dup_trans)
                                duplicate_ids.append(dup_trans.id)

                            bulk_upload.duplicate_count += 1
                            continue

                    # Create transaction
                    month_id = trans_data.month_id or trans_data.date.strftime("%Y-%m")
                    plaid_id = f"MANUAL_{user_id}_{int(datetime.now().timestamp() * 1000)}"

                    transaction = Transaction(
                        user_id=user_id,
                        card_id=trans_data.card_id,
                        plaid_transaction_id=plaid_id,
                        name=trans_data.description,
                        merchant_name=trans_data.merchant,
                        date=trans_data.date,
                        amount=trans_data.amount,
                        month_id=month_id,
                        is_manual=True,
                        currency=trans_data.currency,
                        is_shared=trans_data.is_shared,
                        notes=trans_data.notes,
                        transaction_type_id=trans_data.transaction_type_id,
                        expense_category_id=trans_data.expense_category_id,
                        expense_subcategory_id=trans_data.expense_subcategory_id,
                        payment_method_id=trans_data.payment_method_id,
                        budget_type_id=trans_data.budget_type_id,
                    )

                    db.add(transaction)
                    await db.commit()
                    await db.refresh(transaction)

                    # Link transaction to bulk upload
                    trans_upload = TransactionUpload(
                        transaction_id=transaction.id,
                        bulk_upload_id=bulk_upload.id,
                        row_number=idx,
                        csv_row_data=trans_data.dict()
                    )
                    db.add(trans_upload)
                    await db.commit()

                    created_transactions.append(ManualTransactionResponse.from_orm(transaction))
                    bulk_upload.successful_count += 1

                except Exception as e:
                    logger.error(f"Error processing row {idx}: {e}")
                    failed_rows.append({
                        "row": idx,
                        "error": str(e),
                        "data": trans_data.dict()
                    })
                    bulk_upload.failed_count += 1

            # Update bulk upload status
            if bulk_upload.duplicate_count > 0 and not bulk_request.allow_duplicates:
                bulk_upload.status = "PENDING_REVIEW"
            elif bulk_upload.failed_count == 0:
                bulk_upload.status = "COMPLETED"
            else:
                bulk_upload.status = "PARTIAL_FAILURE"

            bulk_upload.processed_at = datetime.utcnow()
            await db.commit()

            # Audit log
            await logging_service.audit_log(
                event_type="BULK_CREATE",
                resource_type="TRANSACTION",
                user_id=user_id,
                action=f"Bulk uploaded {bulk_upload.successful_count} transactions, {bulk_upload.failed_count} failed, {bulk_upload.duplicate_count} duplicates",
                is_successful="SUCCESS" if bulk_upload.failed_count == 0 else "PARTIAL",
                meta={
                    "bulk_upload_id": bulk_upload.id,
                    "successful": bulk_upload.successful_count,
                    "failed": bulk_upload.failed_count,
                    "duplicates": bulk_upload.duplicate_count
                }
            )

            logger.info(f"Bulk upload {bulk_upload.id} completed: {bulk_upload.successful_count} success, {bulk_upload.failed_count} failed, {bulk_upload.duplicate_count} duplicates")

            return BulkUploadResponse(
                bulk_upload_id=bulk_upload.id,
                total_rows=bulk_upload.total_rows,
                successful_count=bulk_upload.successful_count,
                failed_count=bulk_upload.failed_count,
                duplicate_count=bulk_upload.duplicate_count,
                status=bulk_upload.status,
                error_message=None if bulk_upload.failed_count == 0 else f"{bulk_upload.failed_count} rows failed to import",
                created_transactions=created_transactions,
                failed_rows=failed_rows
            )

        except Exception as e:
            logger.error(f"Error in bulk transaction creation: {e}")
            await db.rollback()
            raise

    async def _find_duplicates(
        self,
        user_id: int,
        card_id: int,
        trans_date: date,
        amount: float,
        category_id: Optional[int],
        db: AsyncSession
    ) -> List[Transaction]:
        """
        Find potential duplicate transactions

        Duplicates are identified when:
        - Same date
        - Same card
        - Same amount (or within 0.01 variance for rounding errors)
        - Same category

        Args:
            user_id: User ID
            card_id: Card ID
            trans_date: Transaction date
            amount: Transaction amount
            category_id: Expense category ID
            db: Database session

        Returns:
            List of potential duplicate transactions
        """
        # Allow for small rounding differences
        amount_variance = 0.01

        query = select(Transaction).where(
            and_(
                Transaction.user_id == user_id,
                Transaction.card_id == card_id,
                Transaction.date == trans_date,
                Transaction.amount >= amount - amount_variance,
                Transaction.amount <= amount + amount_variance,
            )
        )

        if category_id:
            query = query.where(Transaction.expense_category_id == category_id)

        result = await db.execute(query)
        return result.scalars().all()

    async def update_transaction(
        self,
        transaction_id: int,
        transaction_data: ManualTransactionUpdate,
        user_id: int,
        db: AsyncSession
    ) -> Optional[ManualTransactionResponse]:
        """Update a manual transaction"""
        try:
            result = await db.execute(
                select(Transaction).where(
                    and_(Transaction.id == transaction_id, Transaction.user_id == user_id)
                )
            )
            transaction = result.scalars().first()

            if not transaction:
                return None

            # Store old values for audit log
            old_values = {
                "amount": transaction.amount,
                "date": str(transaction.date),
                "category_id": transaction.expense_category_id
            }

            # Update fields
            update_data = transaction_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if value is not None:
                    setattr(transaction, field, value)

            await db.commit()
            await db.refresh(transaction)

            # Audit log
            await logging_service.audit_log(
                event_type="UPDATE",
                resource_type="TRANSACTION",
                resource_id=str(transaction.id),
                user_id=user_id,
                action=f"Updated transaction: {transaction.name}",
                is_successful="SUCCESS",
                changes={"before": old_values, "after": update_data}
            )

            # Invalidate caches
            await self._invalidate_user_transaction_caches(user_id, transaction.month_id)

            return ManualTransactionResponse.from_orm(transaction)

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
        """Delete a manual transaction"""
        try:
            result = await db.execute(
                select(Transaction).where(
                    and_(Transaction.id == transaction_id, Transaction.user_id == user_id)
                )
            )
            transaction = result.scalars().first()

            if not transaction:
                return False

            month_id = transaction.month_id
            trans_name = transaction.name

            # Delete related transaction upload records
            upload_result = await db.execute(
                select(TransactionUpload).where(TransactionUpload.transaction_id == transaction_id)
            )
            uploads = upload_result.scalars().all()
            for upload in uploads:
                await db.delete(upload)

            await db.delete(transaction)
            await db.commit()

            # Audit log
            await logging_service.audit_log(
                event_type="DELETE",
                resource_type="TRANSACTION",
                resource_id=str(transaction_id),
                user_id=user_id,
                action=f"Deleted transaction: {trans_name}",
                is_successful="SUCCESS"
            )

            # Invalidate caches
            await self._invalidate_user_transaction_caches(user_id, month_id)

            return True

        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            await db.rollback()
            raise

    async def _invalidate_user_transaction_caches(self, user_id: int, month_id: Optional[str] = None):
        """Invalidate all transaction-related caches for a user"""
        try:
            await self.cache.delete_pattern(f"transactions:{user_id}:*")
            await self.cache.delete_pattern(f"transaction_summary:{user_id}:*")
            await self.cache.delete_pattern(f"transactions_by_category:{user_id}:*")
            logger.debug(f"Invalidated transaction caches for user {user_id}")
        except Exception as e:
            logger.error(f"Error invalidating transaction caches: {e}")

    async def get_bulk_upload_status(
        self,
        bulk_upload_id: int,
        user_id: int,
        db: AsyncSession
    ) -> Optional[BulkUpload]:
        """Get status of a bulk upload"""
        result = await db.execute(
            select(BulkUpload).where(
                and_(BulkUpload.id == bulk_upload_id, BulkUpload.user_id == user_id)
            ).options(
                selectinload(BulkUpload.duplicate_transactions),
                selectinload(BulkUpload.transaction_uploads)
            )
        )
        return result.scalars().first()
