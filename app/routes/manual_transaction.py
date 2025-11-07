"""
Manual Transaction Routes
Endpoints for creating, reading, updating, and deleting manual transactions
Includes CSV bulk upload and duplicate handling
"""
import os
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.cache import get_cache, RedisCache
from app.services.manual_transaction_service import ManualTransactionService
from app.schemas.manual_transaction import (
    ManualTransactionCreate, ManualTransactionUpdate, ManualTransactionResponse,
    BulkTransactionCreateRequest, BulkUploadResponse, TransactionMetadataResponse,
    DuplicateConfirmationRequest
)
from app.models.user import User as UserModel
from app.models import (
    TransactionType, ExpenseCategory, ExpenseSubcategory,
    PaymentMethod, BudgetType
)

router = APIRouter(prefix="/transactions/manual", tags=["manual_transactions"])

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"


async def get_current_user_id(request: Request, db: AsyncSession = Depends(get_db)) -> int:
    """Extract current user ID from JWT token"""
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


@router.post("/", response_model=ManualTransactionResponse)
async def create_manual_transaction(
    transaction: ManualTransactionCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """
    Create a single manual transaction

    ### Request Body
    - `date`: Transaction date (YYYY-MM-DD format, cannot be in future, max 2 years old)
    - `amount`: Transaction amount (must be positive)
    - `currency`: USD or CAD
    - `description`: Transaction description
    - `merchant`: Merchant name (optional)
    - `notes`: Additional notes (optional)
    - `transaction_type_id`: Type ID (Income, Expense, Transfer, etc.)
    - `expense_category_id`: Category ID (Food, Transportation, etc.)
    - `expense_subcategory_id`: Subcategory ID (optional)
    - `payment_method_id`: Payment method ID (Credit Card, Cash, etc.)
    - `budget_type_id`: Budget type ID (Essential, Discretionary, etc.)
    - `card_id`: Associated card ID
    - `is_shared`: Whether to share with family group

    ### Returns
    Created transaction with ID and timestamps
    """
    try:
        service = ManualTransactionService(cache)
        return await service.create_manual_transaction(
            transaction, user_id, transaction.card_id, db, transaction.is_shared
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create transaction: {str(e)}")


@router.post("/bulk", response_model=BulkUploadResponse)
async def bulk_create_transactions(
    bulk_request: BulkTransactionCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """
    Bulk create transactions from CSV upload

    ### Request Body
    - `transactions`: List of transactions (max 1000)
    - `filename`: Original CSV filename
    - `allow_duplicates`: Whether to skip duplicate checks

    ### Response
    - `bulk_upload_id`: ID of the bulk upload record
    - `successful_count`: Number of successfully imported transactions
    - `failed_count`: Number of failed imports
    - `duplicate_count`: Number of duplicates found
    - `status`: Upload status (COMPLETED, PARTIAL_FAILURE, PENDING_REVIEW)
    - `created_transactions`: List of created transactions
    - `failed_rows`: Details of failed rows

    ### Duplicate Handling
    Duplicates are identified by:
    - Same date
    - Same card
    - Same amount (±$0.01 variance)
    - Same category

    If duplicates found and `allow_duplicates=false`, they're flagged for review.
    """
    try:
        service = ManualTransactionService(cache)
        return await service.create_bulk_transactions(
            bulk_request, user_id, db, check_duplicates=True
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Bulk upload failed: {str(e)}")


@router.put("/{transaction_id}", response_model=ManualTransactionResponse)
async def update_manual_transaction(
    transaction_id: int,
    transaction_data: ManualTransactionUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """
    Update a manual transaction

    ### Path Parameters
    - `transaction_id`: ID of transaction to update

    ### Request Body
    All fields are optional. Only provided fields will be updated.

    ### Returns
    Updated transaction
    """
    try:
        service = ManualTransactionService(cache)
        result = await service.update_transaction(
            transaction_id, transaction_data, user_id, db
        )

        if not result:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update transaction: {str(e)}")


@router.delete("/{transaction_id}")
async def delete_manual_transaction(
    transaction_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """
    Delete a manual transaction

    ### Path Parameters
    - `transaction_id`: ID of transaction to delete

    ### Returns
    Success message
    """
    try:
        service = ManualTransactionService(cache)
        success = await service.delete_transaction(transaction_id, user_id, db)

        if not success:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return {"message": "Transaction deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete transaction: {str(e)}")


@router.get("/metadata", response_model=TransactionMetadataResponse)
async def get_transaction_metadata(
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """
    Get all transaction metadata (cached)

    Returns transaction types, expense categories, payment methods, and budget types.
    Results are cached for 1 hour.

    ### Returns
    - `transaction_types`: List of available transaction types
    - `expense_categories`: List of expense categories with subcategories
    - `payment_methods`: List of payment methods
    - `budget_types`: List of budget classifications
    """
    try:
        # Try cache first
        cache_key = "transaction_metadata:all"
        cached_data = await cache.get(cache_key)
        if cached_data:
            return TransactionMetadataResponse(**cached_data)

        # Fetch from database
        async def fetch_from_db():
            result = await db.execute(select(TransactionType).where(TransactionType.is_active == True))
            trans_types = result.scalars().all()

            result = await db.execute(select(ExpenseCategory).where(ExpenseCategory.is_active == True))
            categories = result.scalars().all()

            result = await db.execute(select(PaymentMethod).where(PaymentMethod.is_active == True))
            methods = result.scalars().all()

            result = await db.execute(select(BudgetType).where(BudgetType.is_active == True))
            budget_types = result.scalars().all()

            return {
                "transaction_types": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "description": t.description,
                        "icon": t.icon,
                        "color": t.color
                    }
                    for t in trans_types
                ],
                "expense_categories": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "description": c.description,
                        "icon": c.icon,
                        "color": c.color,
                        "bg_color": c.bg_color,
                        "display_order": c.display_order
                    }
                    for c in categories
                ],
                "payment_methods": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "description": m.description,
                        "icon": m.icon,
                        "color": m.color,
                        "display_order": m.display_order
                    }
                    for m in methods
                ],
                "budget_types": [
                    {
                        "id": b.id,
                        "name": b.name,
                        "description": b.description,
                        "icon": b.icon,
                        "color": b.color,
                        "display_order": b.display_order
                    }
                    for b in budget_types
                ]
            }

        data = await fetch_from_db()

        # Cache for 1 hour
        await cache.set(cache_key, data, expire=3600)

        return TransactionMetadataResponse(**data)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch metadata: {str(e)}")


@router.get("/bulk/{bulk_upload_id}")
async def get_bulk_upload_status(
    bulk_upload_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """
    Get status of a bulk upload

    ### Path Parameters
    - `bulk_upload_id`: ID of bulk upload to check

    ### Returns
    Bulk upload details including status, counts, and any duplicates
    """
    try:
        service = ManualTransactionService(cache)
        bulk_upload = await service.get_bulk_upload_status(bulk_upload_id, user_id, db)

        if not bulk_upload:
            raise HTTPException(status_code=404, detail="Bulk upload not found")

        return {
            "bulk_upload_id": bulk_upload.id,
            "filename": bulk_upload.filename,
            "total_rows": bulk_upload.total_rows,
            "successful_count": bulk_upload.successful_count,
            "failed_count": bulk_upload.failed_count,
            "duplicate_count": bulk_upload.duplicate_count,
            "status": bulk_upload.status,
            "uploaded_at": bulk_upload.uploaded_at,
            "processed_at": bulk_upload.processed_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch bulk upload status: {str(e)}")


@router.post("/duplicates/confirm")
async def confirm_duplicate_handling(
    confirmation: DuplicateConfirmationRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """
    Confirm handling of duplicate transactions

    After bulk upload identifies duplicates, user can accept or reject them.

    ### Request Body
    - `duplicate_transaction_ids`: List of duplicate IDs to handle
    - `action`: 'ACCEPT' to keep duplicates, 'REJECT' to discard
    - `user_notes`: Optional notes about the decision

    ### Returns
    Confirmation status and any transactions that were created
    """
    try:
        # TODO: Implement duplicate confirmation logic
        return {
            "status": "confirmed",
            "action": confirmation.action,
            "duplicates_processed": len(confirmation.duplicate_transaction_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to confirm duplicates: {str(e)}")
