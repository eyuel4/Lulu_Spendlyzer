import os
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid import ApiClient, Configuration
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.card import Card
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.plaid import (
    LinkTokenResponse, PlaidSyncResponse, PlaidAccountResponse, PlaidDisconnectResponse
)

logger = logging.getLogger(__name__)


class PlaidService:
    def __init__(self):
        """Initialize Plaid client with credentials from environment"""
        self.client_id = os.getenv('PLAID_CLIENT_ID')
        self.secret = os.getenv('PLAID_SECRET')
        self.env = os.getenv('PLAID_ENV', 'sandbox')
        self.webhook_url = os.getenv('PLAID_WEBHOOK_URL')
        
        if not self.client_id or not self.secret:
            logger.error("Plaid credentials not found in environment variables")
            raise ValueError("PLAID_CLIENT_ID and PLAID_SECRET must be set")
        
        # Configure Plaid client
        configuration = Configuration(
            host=self._get_plaid_host(),
            api_key={
                'clientId': self.client_id,
                'secret': self.secret,
            }
        )
        
        api_client = ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)
        
        logger.info(f"Plaid service initialized with environment: {self.env}")

    def _get_plaid_host(self) -> str:
        """Get Plaid API host based on environment"""
        hosts = {
            'sandbox': 'https://sandbox.plaid.com',
            'development': 'https://development.plaid.com',
            'production': 'https://production.plaid.com'
        }
        return hosts.get(self.env, 'https://sandbox.plaid.com')

    async def create_link_token(self, user_id: int, db: AsyncSession) -> LinkTokenResponse:
        """
        Create a Plaid Link token for user to connect their bank account
        
        Args:
            user_id: ID of the user connecting their account
            db: Database session
            
        Returns:
            LinkTokenResponse with link_token and expiration
        """
        try:
            # Get user from database
            result = await db.execute(select(User).filter(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            # Create link token request
            request = LinkTokenCreateRequest(
                user=LinkTokenCreateRequestUser(
                    client_user_id=str(user_id)
                ),
                client_name="Lulu Spendlyzer",
                products=[Products("transactions"), Products("auth")],
                country_codes=[CountryCode("US"), CountryCode("CA")],
                language='en',
                webhook=self.webhook_url if self.webhook_url else None,
            )
            
            response = self.client.link_token_create(request)
            
            logger.info(f"Link token created for user {user_id}")
            
            # Convert expiration datetime to ISO string format
            expiration = response['expiration']
            if isinstance(expiration, datetime):
                expiration_str = expiration.isoformat()
            else:
                expiration_str = str(expiration)
            
            return LinkTokenResponse(
                link_token=response['link_token'],
                expiration=expiration_str
            )
            
        except Exception as e:
            logger.error(f"Error creating link token: {e}")
            raise

    async def exchange_public_token(
        self,
        public_token: str,
        user_id: int,
        institution_name: Optional[str],
        institution_id: Optional[str],
        accounts: Optional[List[dict]],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Exchange public token for access token and save card
        
        Args:
            public_token: Public token from Plaid Link
            user_id: ID of the user
            institution_name: Name of the financial institution
            institution_id: Plaid institution ID
            accounts: List of accounts from Plaid
            db: Database session
            
        Returns:
            Dict with card info and sync results
        """
        try:
            # Exchange public token for access token
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)
            
            access_token = response['access_token']
            item_id = response['item_id']
            
            logger.info(f"Token exchanged successfully for user {user_id}, item_id: {item_id}")
            
            # Get account details if not provided
            if not accounts or not institution_name:
                accounts_request = AccountsGetRequest(access_token=access_token)
                accounts_response = self.client.accounts_get(accounts_request)
                accounts = accounts_response['accounts']
                institution_name = accounts_response.get('item', {}).get('institution_id', 'Bank Account')
            
            # Use the first account for the card
            account = accounts[0] if accounts else {}
            account_name = account.get('name', 'Primary Account')
            account_mask = account.get('mask', '0000')
            
            # Create card record
            new_card = Card(
                user_id=user_id,
                bank_name=institution_name or "Bank Account",
                card_name=account_name,
                last4=account_mask,
                access_token=access_token,
                plaid_item_id=item_id,
                plaid_institution_id=institution_id,
                last_sync_date=None
            )
            
            db.add(new_card)
            await db.commit()
            
            # Get the card ID (safe to access before commit expires the object)
            card_id = new_card.id
            
            # Query the card again to ensure all attributes are loaded properly
            # This avoids the greenlet error from accessing expired attributes
            result = await db.execute(select(Card).filter(Card.id == card_id))
            card = result.scalar_one()
            
            logger.info(f"Card created with ID {card.id} for user {user_id}")
            
            # Trigger initial sync
            sync_result = await self.sync_transactions(card.id, db)
            
            # Re-query the card after sync to get updated last_sync_date and avoid expired object issues
            # The sync_transactions method commits, which can expire the card object
            result_after_sync = await db.execute(select(Card).filter(Card.id == card_id))
            card_after_sync = result_after_sync.scalar_one()
            
            # Extract all attributes immediately to avoid any lazy loading issues
            # Access all attributes in one go while the object is fresh
            card_id_val = card_after_sync.id
            bank_name_val = card_after_sync.bank_name
            card_name_val = card_after_sync.card_name
            last4_val = card_after_sync.last4
            plaid_item_id_val = card_after_sync.plaid_item_id
            plaid_institution_id_val = card_after_sync.plaid_institution_id
            last_sync_date_val = card_after_sync.last_sync_date
            created_at_val = card_after_sync.created_at or datetime.now()
            updated_at_val = card_after_sync.updated_at
            
            # Manually construct response using extracted values
            card_response = PlaidAccountResponse(
                id=card_id_val,
                bank_name=bank_name_val,
                card_name=card_name_val,
                last4=last4_val,
                plaid_item_id=plaid_item_id_val,
                plaid_institution_id=plaid_institution_id_val,
                last_sync_date=last_sync_date_val,
                created_at=created_at_val,
                updated_at=updated_at_val
            )
            
            return {
                "card": card_response,
                "sync": sync_result
            }
            
        except Exception as e:
            logger.error(f"Error exchanging public token: {e}")
            await db.rollback()
            raise

    async def sync_transactions(
        self,
        card_id: int,
        db: AsyncSession,
        days: int = 30
    ) -> PlaidSyncResponse:
        """
        Sync transactions from Plaid for a specific card
        
        Args:
            card_id: ID of the card to sync
            db: Database session
            days: Number of days to look back (default 30)
            
        Returns:
            PlaidSyncResponse with sync results
        """
        try:
            # Get card from database
            result = await db.execute(select(Card).filter(Card.id == card_id))
            card = result.scalar_one_or_none()
            
            if not card:
                raise ValueError(f"Card with ID {card_id} not found")
            
            if not card.access_token:
                raise ValueError(f"Card {card_id} does not have an access token")
            
            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # Fetch transactions from Plaid
            request = TransactionsGetRequest(
                access_token=card.access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(
                    count=500,
                    offset=0
                )
            )
            
            response = self.client.transactions_get(request)
            plaid_transactions = response['transactions']
            
            logger.info(f"Fetched {len(plaid_transactions)} transactions from Plaid for card {card_id}")
            
            # Get existing transaction IDs to avoid duplicates
            existing_result = await db.execute(
                select(Transaction.plaid_transaction_id).filter(
                    Transaction.card_id == card_id,
                    Transaction.plaid_transaction_id.isnot(None)
                )
            )
            existing_ids = {row[0] for row in existing_result.all()}
            
            transactions_added = 0
            transactions_updated = 0
            
            # Process each transaction
            for plaid_txn in plaid_transactions:
                transaction_id = plaid_txn['transaction_id']
                
                # Skip if already exists
                if transaction_id in existing_ids:
                    continue
                
                # Calculate month_id
                txn_date = plaid_txn['date']
                month_id = f"{txn_date.strftime('%B_%Y')}"
                
                # Get category (first one if available)
                plaid_category = plaid_txn.get('category', [None])[0] if plaid_txn.get('category') else None
                
                # Create transaction
                transaction = Transaction(
                    user_id=card.user_id,
                    card_id=card.id,
                    plaid_transaction_id=transaction_id,
                    name=plaid_txn['name'],
                    merchant_name=plaid_txn.get('merchant_name'),
                    date=txn_date,
                    amount=-plaid_txn['amount'],  # Plaid uses positive for debits, we use negative
                    plaid_category=plaid_category,
                    month_id=month_id,
                    is_manual=False
                )
                
                db.add(transaction)
                transactions_added += 1
            
            # Update card sync date
            card.last_sync_date = datetime.now()
            
            await db.commit()
            
            logger.info(f"Sync completed for card {card_id}: {transactions_added} added, {transactions_updated} updated")
            
            return PlaidSyncResponse(
                success=True,
                message=f"Successfully synced {transactions_added} new transactions",
                transactions_added=transactions_added,
                transactions_updated=transactions_updated,
                card_id=card_id,
                sync_date=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error syncing transactions for card {card_id}: {e}")
            await db.rollback()
            raise

    async def get_accounts(self, user_id: int, db: AsyncSession) -> List[PlaidAccountResponse]:
        """
        Get all connected Plaid accounts for a user
        
        Args:
            user_id: ID of the user
            db: Database session
            
        Returns:
            List of PlaidAccountResponse
        """
        try:
            result = await db.execute(
                select(Card).filter(Card.user_id == user_id)
            )
            cards = result.scalars().all()
            
            # Manually construct responses to avoid async SQLAlchemy issues
            # Access attributes directly - they're already loaded from the query
            accounts = []
            for card in cards:
                accounts.append(PlaidAccountResponse(
                    id=card.id,
                    bank_name=card.bank_name,
                    card_name=card.card_name,
                    last4=card.last4,
                    plaid_item_id=card.plaid_item_id,
                    plaid_institution_id=card.plaid_institution_id,
                    last_sync_date=card.last_sync_date,
                    created_at=card.created_at,
                    updated_at=card.updated_at
                ))
            
            return accounts
            
        except Exception as e:
            logger.error(f"Error getting accounts for user {user_id}: {e}")
            raise

    async def remove_item(self, card_id: int, db: AsyncSession) -> PlaidDisconnectResponse:
        """
        Disconnect a Plaid connection and remove card
        
        Args:
            card_id: ID of the card to disconnect
            db: Database session
            
        Returns:
            PlaidDisconnectResponse
        """
        try:
            # Get card from database
            result = await db.execute(select(Card).filter(Card.id == card_id))
            card = result.scalar_one_or_none()
            
            if not card:
                raise ValueError(f"Card with ID {card_id} not found")
            
            # Remove item from Plaid
            if card.access_token:
                try:
                    request = ItemRemoveRequest(access_token=card.access_token)
                    self.client.item_remove(request)
                    logger.info(f"Plaid item removed for card {card_id}")
                except Exception as plaid_error:
                    logger.warning(f"Error removing Plaid item: {plaid_error}")
                    # Continue with local deletion even if Plaid fails
            
            # Delete card (transactions will be cascade deleted)
            await db.delete(card)
            await db.commit()
            
            logger.info(f"Card {card_id} disconnected and removed")
            
            return PlaidDisconnectResponse(
                success=True,
                message="Bank account disconnected successfully",
                card_id=card_id
            )
            
        except Exception as e:
            logger.error(f"Error disconnecting card {card_id}: {e}")
            await db.rollback()
            raise

