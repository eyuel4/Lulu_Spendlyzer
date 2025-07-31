from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.models.family_group import FamilyGroup
from app.models.user import User as UserModel
from app.models.invitation import Invitation
from app.core.cache import RedisCache, CacheKeys
import logging

logger = logging.getLogger(__name__)

class FamilyService:
    def __init__(self, cache: RedisCache):
        self.cache = cache

    async def get_family_group(
        self, 
        family_id: int, 
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get family group with caching"""
        cache_key = CacheKeys.family_group(family_id)
        
        # Try cache first
        cached_family = await self.cache.get(cache_key)
        if cached_family:
            logger.debug(f"Cache HIT: family group {family_id}")
            return cached_family
        
        # Get from database
        result = await db.execute(
            select(FamilyGroup)
            .where(FamilyGroup.id == family_id)
            .options(selectinload(FamilyGroup.owner))
        )
        family_group = result.scalars().first()
        
        if not family_group:
            return None
        
        # Convert to dict
        family_data = {
            'id': family_group.id,
            'owner_user_id': family_group.owner_user_id,
            'created_at': family_group.created_at.isoformat(),
            'owner': {
                'id': family_group.owner.id,
                'first_name': family_group.owner.first_name,
                'last_name': family_group.owner.last_name,
                'email': family_group.owner.email
            } if family_group.owner else None
        }
        
        # Cache the result
        await self.cache.set(cache_key, family_data, expire=7200)  # 2 hours
        
        return family_data

    async def get_family_members(
        self, 
        family_id: int, 
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get family members with caching"""
        cache_key = CacheKeys.family_members(family_id)
        
        # Try cache first
        cached_members = await self.cache.get(cache_key)
        if cached_members:
            logger.debug(f"Cache HIT: family members {family_id}")
            return cached_members
        
        # Get from database
        result = await db.execute(
            select(UserModel)
            .where(UserModel.family_group_id == family_id)
        )
        members = result.scalars().all()
        
        # Convert to list of dicts
        members_data = []
        for member in members:
            member_data = {
                'id': member.id,
                'first_name': member.first_name,
                'last_name': member.last_name,
                'email': member.email,
                'is_primary': member.is_primary,
                'created_at': member.created_at.isoformat() if member.created_at else None
            }
            members_data.append(member_data)
        
        # Cache the result
        await self.cache.set(cache_key, members_data, expire=3600)  # 1 hour
        
        return members_data

    async def get_user_family(
        self, 
        user_id: int, 
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get user's family group with caching"""
        cache_key = f"user_family:{user_id}"
        
        # Try cache first
        cached_user_family = await self.cache.get(cache_key)
        if cached_user_family:
            logger.debug(f"Cache HIT: user family {user_id}")
            return cached_user_family
        
        # Get user with family group
        result = await db.execute(
            select(UserModel)
            .where(UserModel.id == user_id)
            .options(selectinload(UserModel.family_group))
        )
        user = result.scalars().first()
        
        if not user or user.family_group_id is None:
            return None
        
        family_group_id = int(user.family_group_id) if user.family_group_id is not None else 0
        
        # Get family group data
        family_data = await self.get_family_group(family_group_id, db)
        if not family_data:
            return None
        
        # Get family members
        members_data = await self.get_family_members(family_group_id, db)
        
        user_family_data = {
            'family_group': family_data,
            'members': members_data,
            'user_role': 'owner' if bool(user.is_primary) else 'member'
        }
        
        # Cache the result
        await self.cache.set(cache_key, user_family_data, expire=3600)  # 1 hour
        
        return user_family_data

    async def create_family_group(
        self, 
        owner_user_id: int, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Create a new family group with cache invalidation"""
        try:
            # Create family group
            family_group = FamilyGroup(
                owner_user_id=owner_user_id,
                created_at=datetime.now(timezone.utc)
            )
            db.add(family_group)
            await db.flush()  # Get family_group.id
            
            # Update user with family_group_id
            result = await db.execute(select(UserModel).where(UserModel.id == owner_user_id))
            user = result.scalars().first()
            if user:
                user.family_group_id = family_group.id
                user.is_primary = True
                db.add(user)
            
            await db.commit()
            await db.refresh(family_group)
            
            # Invalidate related caches
            await self._invalidate_family_caches(family_group.id, owner_user_id)
            
            return await self.get_family_group(family_group.id, db)
            
        except Exception as e:
            logger.error(f"Error creating family group: {e}")
            await db.rollback()
            raise

    async def add_family_member(
        self, 
        family_id: int, 
        member_data: Dict[str, Any], 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Add a member to family group with cache invalidation"""
        try:
            # Create invitation
            invitation = Invitation(
                family_group_id=family_id,
                email=member_data['email'],
                first_name=member_data['first_name'],
                last_name=member_data['last_name'],
                role=member_data['role'],
                status='pending',
                token=secrets.token_urlsafe(32),
                sent_at=datetime.now(timezone.utc)
            )
            db.add(invitation)
            await db.commit()
            
            # Invalidate family caches
            await self._invalidate_family_caches(family_id)
            
            return {
                'invitation_id': invitation.id,
                'email': invitation.email,
                'status': invitation.status,
                'token': invitation.token
            }
            
        except Exception as e:
            logger.error(f"Error adding family member: {e}")
            await db.rollback()
            raise

    async def get_family_invitations(
        self, 
        family_id: int, 
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get family invitations with caching"""
        cache_key = f"family_invitations:{family_id}"
        
        # Try cache first
        cached_invitations = await self.cache.get(cache_key)
        if cached_invitations:
            logger.debug(f"Cache HIT: family invitations {family_id}")
            return cached_invitations
        
        # Get from database
        result = await db.execute(
            select(Invitation)
            .where(Invitation.family_group_id == family_id)
            .order_by(Invitation.sent_at.desc())
        )
        invitations = result.scalars().all()
        
        # Convert to list of dicts
        invitations_data = []
        for invitation in invitations:
            invitation_data = {
                'id': invitation.id,
                'email': invitation.email,
                'first_name': invitation.first_name,
                'last_name': invitation.last_name,
                'role': invitation.role,
                'status': invitation.status,
                'sent_at': invitation.sent_at.isoformat() if invitation.sent_at else None
            }
            invitations_data.append(invitation_data)
        
        # Cache the result
        await self.cache.set(cache_key, invitations_data, expire=1800)  # 30 minutes
        
        return invitations_data

    async def accept_family_invitation(
        self, 
        token: str, 
        user_id: int, 
        db: AsyncSession
    ) -> bool:
        """Accept family invitation with cache invalidation"""
        try:
            # Get invitation
            result = await db.execute(
                select(Invitation)
                .where(Invitation.token == token)
                .where(Invitation.status == 'pending')
            )
            invitation = result.scalars().first()
            
            if not invitation:
                return False
            
            # Update invitation status
            invitation.status = 'accepted'
            invitation.accepted_at = datetime.now(timezone.utc)
            db.add(invitation)
            
            # Add user to family group
            result = await db.execute(select(UserModel).where(UserModel.id == user_id))
            user = result.scalars().first()
            if user:
                user.family_group_id = invitation.family_group_id
                user.is_primary = False
                db.add(user)
            
            await db.commit()
            
            # Invalidate family caches
            await self._invalidate_family_caches(invitation.family_group_id, user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error accepting family invitation: {e}")
            await db.rollback()
            return False

    async def _invalidate_family_caches(self, family_id: int, user_id: Optional[int] = None):
        """Invalidate all family-related caches"""
        try:
            # Delete family group caches
            await self.cache.delete(CacheKeys.family_group(family_id))
            await self.cache.delete(CacheKeys.family_members(family_id))
            await self.cache.delete_pattern(f"family_invitations:{family_id}")
            
            # Delete user family cache if user_id provided
            if user_id:
                await self.cache.delete(f"user_family:{user_id}")
            
            logger.debug(f"Invalidated family caches for family {family_id}")
            
        except Exception as e:
            logger.error(f"Error invalidating family caches: {e}")

# Import required modules
from datetime import datetime, timezone
import secrets 