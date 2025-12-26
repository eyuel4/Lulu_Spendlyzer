import asyncio
import logging
from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.card import Card
from app.services.plaid_service import PlaidService
import os

logger = logging.getLogger(__name__)


class PlaidSyncJob:
    """Background job to sync transactions from all connected Plaid accounts"""
    
    def __init__(self):
        self.plaid_service = PlaidService()
        
        # Create async engine for background job
        db_url = os.getenv('DB_URL', 'sqlite+aiosqlite:///./finance.db')
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def sync_all_accounts(self) -> dict:
        """
        Sync transactions for all connected bank accounts
        
        Returns:
            Dict with sync results
        """
        logger.info("Starting background sync for all Plaid accounts")
        
        results = {
            "total_accounts": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "total_transactions_added": 0,
            "errors": []
        }
        
        async with self.async_session() as db:
            try:
                # Get all cards with Plaid access tokens
                result = await db.execute(
                    select(Card).filter(
                        Card.access_token.isnot(None),
                        Card.plaid_item_id.isnot(None)
                    )
                )
                cards = result.scalars().all()
                
                results["total_accounts"] = len(cards)
                logger.info(f"Found {len(cards)} Plaid-connected accounts to sync")
                
                # Sync each card
                for card in cards:
                    try:
                        logger.info(f"Syncing card {card.id} ({card.bank_name})")
                        
                        sync_result = await self.plaid_service.sync_transactions(
                            card_id=card.id,
                            db=db,
                            days=30
                        )
                        
                        results["successful_syncs"] += 1
                        results["total_transactions_added"] += sync_result.transactions_added
                        
                        logger.info(
                            f"Successfully synced card {card.id}: "
                            f"{sync_result.transactions_added} transactions added"
                        )
                        
                    except Exception as card_error:
                        results["failed_syncs"] += 1
                        error_msg = f"Error syncing card {card.id}: {str(card_error)}"
                        results["errors"].append(error_msg)
                        logger.error(error_msg)
                        continue
                
                logger.info(
                    f"Background sync completed: "
                    f"{results['successful_syncs']}/{results['total_accounts']} successful, "
                    f"{results['total_transactions_added']} transactions added"
                )
                
            except Exception as e:
                logger.error(f"Error in background sync job: {e}")
                results["errors"].append(str(e))
        
        return results
    
    async def sync_single_account(self, card_id: int) -> dict:
        """
        Sync transactions for a single account
        
        Args:
            card_id: ID of the card to sync
            
        Returns:
            Dict with sync results
        """
        logger.info(f"Starting sync for card {card_id}")
        
        async with self.async_session() as db:
            try:
                sync_result = await self.plaid_service.sync_transactions(
                    card_id=card_id,
                    db=db,
                    days=30
                )
                
                logger.info(
                    f"Successfully synced card {card_id}: "
                    f"{sync_result.transactions_added} transactions added"
                )
                
                return {
                    "success": True,
                    "card_id": card_id,
                    "transactions_added": sync_result.transactions_added
                }
                
            except Exception as e:
                logger.error(f"Error syncing card {card_id}: {e}")
                return {
                    "success": False,
                    "card_id": card_id,
                    "error": str(e)
                }


# Global instance
plaid_sync_job = PlaidSyncJob()


async def run_daily_sync():
    """Run the daily sync job"""
    try:
        results = await plaid_sync_job.sync_all_accounts()
        logger.info(f"Daily sync completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Daily sync failed: {e}")
        raise

