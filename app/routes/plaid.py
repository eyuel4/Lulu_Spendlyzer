from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.services.plaid_service import PlaidService
from app.schemas.plaid import (
    LinkTokenRequest,
    LinkTokenResponse,
    PublicTokenExchange,
    PlaidAccountResponse,
    PlaidSyncResponse,
    PlaidDisconnectResponse,
    PlaidWebhookRequest
)
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plaid", tags=["plaid"])

# Test endpoint to verify router is working
@router.get("/test")
async def test_plaid_router():
    """Test endpoint to verify Plaid router is accessible"""
    return {"status": "ok", "message": "Plaid router is working"}

# Lazy initialization of Plaid service
_plaid_service = None

def get_plaid_service() -> PlaidService:
    """Get or create PlaidService instance"""
    global _plaid_service
    if _plaid_service is None:
        _plaid_service = PlaidService()
    return _plaid_service


@router.post("/create-link-token", response_model=LinkTokenResponse)
async def create_link_token(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Plaid Link token for user to connect their bank account
    """
    logger.info(f"=== CREATE LINK TOKEN REQUEST ===")
    logger.info(f"URL: {request.url}")
    logger.info(f"Method: {request.method}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Path: {request.url.path}")
    
    try:
        plaid_service = get_plaid_service()
        logger.info(f"PlaidService initialized, creating link token...")
        link_token = await plaid_service.create_link_token(user_id, db)
        logger.info(f"Successfully created link token for user {user_id}")
        return link_token
    except ValueError as e:
        logger.error(f"ValueError creating link token: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as he:
        logger.error(f"HTTPException: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Error creating link token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create link token")


@router.post("/exchange-token")
async def exchange_token(
    exchange_request: PublicTokenExchange,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange public token for access token and sync initial transactions
    """
    try:
        plaid_service = get_plaid_service()
        result = await plaid_service.exchange_public_token(
            public_token=exchange_request.public_token,
            user_id=user_id,
            institution_name=exchange_request.institution_name,
            institution_id=exchange_request.institution_id,
            accounts=exchange_request.accounts,
            db=db
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error exchanging token: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect bank account")


@router.get("/accounts", response_model=List[PlaidAccountResponse])
async def get_accounts(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all connected bank accounts for the user
    """
    try:
        plaid_service = get_plaid_service()
        accounts = await plaid_service.get_accounts(user_id, db)
        return accounts
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve accounts")


@router.post("/sync-transactions/{card_id}", response_model=PlaidSyncResponse)
async def sync_transactions(
    card_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually sync transactions for a specific card (last 30 days)
    """
    try:
        # Verify card belongs to user
        from app.models.card import Card
        from sqlalchemy import select
        
        result = await db.execute(
            select(Card).filter(Card.id == card_id, Card.user_id == user_id)
        )
        card = result.scalar_one_or_none()
        
        if not card:
            raise HTTPException(status_code=404, detail="Card not found or access denied")
        
        plaid_service = get_plaid_service()
        sync_result = await plaid_service.sync_transactions(card_id, db)
        return sync_result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error syncing transactions: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync transactions")


@router.delete("/disconnect/{card_id}", response_model=PlaidDisconnectResponse)
async def disconnect_account(
    card_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnect a Plaid bank account connection
    """
    try:
        # Verify card belongs to user
        from app.models.card import Card
        from sqlalchemy import select
        
        result = await db.execute(
            select(Card).filter(Card.id == card_id, Card.user_id == user_id)
        )
        card = result.scalar_one_or_none()
        
        if not card:
            raise HTTPException(status_code=404, detail="Card not found or access denied")
        
        plaid_service = get_plaid_service()
        disconnect_result = await plaid_service.remove_item(card_id, db)
        return disconnect_result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error disconnecting account: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect account")


@router.post("/webhook")
async def plaid_webhook(
    webhook_request: PlaidWebhookRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Plaid webhook events
    Note: This is a basic implementation. In production, verify webhook signature.
    """
    try:
        webhook_type = webhook_request.webhook_type
        webhook_code = webhook_request.webhook_code
        item_id = webhook_request.item_id
        
        logger.info(f"Received webhook: type={webhook_type}, code={webhook_code}, item_id={item_id}")
        
        # Find card by item_id
        from app.models.card import Card
        from sqlalchemy import select
        
        result = await db.execute(
            select(Card).filter(Card.plaid_item_id == item_id)
        )
        card = result.scalar_one_or_none()
        
        if not card:
            logger.warning(f"Card not found for item_id: {item_id}")
            return {"status": "ignored", "reason": "card_not_found"}
        
        # Handle different webhook types
        if webhook_type == "TRANSACTIONS":
            if webhook_code in ["INITIAL_UPDATE", "HISTORICAL_UPDATE", "DEFAULT_UPDATE"]:
                # Trigger transaction sync
                logger.info(f"Triggering sync for card {card.id} due to webhook {webhook_code}")
                plaid_service = get_plaid_service()
                await plaid_service.sync_transactions(card.id, db)
                return {"status": "success", "action": "synced_transactions"}
            
            elif webhook_code == "TRANSACTIONS_REMOVED":
                logger.info(f"Transactions removed webhook for card {card.id}")
                # Could implement logic to handle removed transactions
                return {"status": "acknowledged"}
        
        elif webhook_type == "ITEM":
            if webhook_code == "ERROR":
                logger.error(f"Item error for card {card.id}: {webhook_request.error}")
                # Could notify user or mark card as needing re-authentication
                return {"status": "error_logged"}
            
            elif webhook_code == "LOGIN_REQUIRED":
                logger.warning(f"Login required for card {card.id}")
                # Could notify user to re-authenticate
                return {"status": "acknowledged"}
        
        return {"status": "acknowledged"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # Return 200 to avoid webhook retries
        return {"status": "error", "message": str(e)}

