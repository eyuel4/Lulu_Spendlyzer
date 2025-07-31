from typing import List, Optional, Dict, Any, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.models.family_group import FamilyGroup
from app.models.user import User as UserModel
from app.models.invitation import Invitation
from app.core.cache import RedisCache, CacheKeys
import logging
from datetime import datetime, timezone
import secrets

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
        )
        family_group = result.scalars().first()
        
        if not family_group:
            return None
        
        # Convert to dict
        family_data = {
            'id': family_group.id,
            'owner_user_id': family_group.owner_user_id,
            'created_at': family_group.created_at.isoformat() if family_group.created_at is not None else None
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
                'created_at': member.created_at.isoformat() if member.created_at is not None else None
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
        )
        user = result.scalars().first()
        
        if not user or user.family_group_id is None:
            return None
        
        family_group_id = cast(int, user.family_group_id)
        
        # Get family group data
        family_data = await self.get_family_group(family_group_id, db)
        if not family_data:
            return None
        
        # Get family members
        members_data = await self.get_family_members(family_group_id, db)
        
        user_family_data = {
            'family_group': family_data,
            'members': members_data,
            'user_role': 'owner' if cast(bool, user.is_primary) else 'member'
        }
        
        # Cache the result
        await self.cache.set(cache_key, user_family_data, expire=3600)  # 1 hour
        
        return user_family_data

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
                'sent_at': invitation.sent_at.isoformat() if invitation.sent_at is not None else None
            }
            invitations_data.append(invitation_data)
        
        # Cache the result
        await self.cache.set(cache_key, invitations_data, expire=1800)  # 30 minutes
        
        return invitations_data

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