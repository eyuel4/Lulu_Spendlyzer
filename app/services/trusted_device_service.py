import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, Request
from app.models.trusted_device import TrustedDevice
from app.models.user import User
from app.core.device_fingerprint import DeviceFingerprint
from app.services.logging_service import logging_service

class TrustedDeviceService:
    """Service for managing trusted devices with enhanced security"""
    
    def __init__(self):
        self.token_length = 32
        self.default_expiration_days = 7
        self.max_devices_per_user = 5
    
    def generate_secure_token(self) -> str:
        """Generate a cryptographically secure random token"""
        return secrets.token_urlsafe(self.token_length)
    
    def hash_token(self, token: str) -> str:
        """Hash token before storing in database"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def create_trusted_device(
        self, 
        user_id: int, 
        request: Request, 
        remember_device: bool = True,
        expiration_days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new trusted device for the user
        
        Args:
            user_id: User ID
            request: FastAPI request object
            remember_device: Whether to remember this device
            expiration_days: Number of days until expiration
            
        Returns:
            Dictionary with token and device info, or None if not remembered
        """
        if not remember_device:
            return None
        
        # Extract device information
        device_info = DeviceFingerprint.extract_device_info_from_request(request)
        
        # Generate secure token
        token = self.generate_secure_token()
        token_hash = self.hash_token(token)
        
        # Create expiration date
        expires_at = TrustedDevice.create_expiration_date(expiration_days)
        
        # Create trusted device record
        trusted_device = TrustedDevice(
            user_id=user_id,
            device_hash=device_info["device_hash"],
            token_hash=token_hash,
            device_name=device_info["device_name"],
            user_agent=device_info["user_agent"],
            ip_address=device_info["ip_address"],
            location=device_info["location"],
            country_code=device_info["country_code"],
            expires_at=expires_at
        )
        
        return {
            "token": token,
            "device_info": device_info,
            "trusted_device": trusted_device
        }
    
    async def save_trusted_device(self, db: AsyncSession, trusted_device: TrustedDevice) -> TrustedDevice:
        """Save trusted device to database"""
        # Check device limit
        await self._enforce_device_limit(db, trusted_device.user_id)
        
        # Clean up expired devices
        await self._cleanup_expired_devices(db, trusted_device.user_id)
        
        db.add(trusted_device)
        await db.commit()
        await db.refresh(trusted_device)
        
        # Log the creation
        await logging_service.log_audit_event(
            event_type="trusted_device_created",
            resource_type="trusted_device",
            action="create",
            user_id=trusted_device.user_id,
            resource_id=str(trusted_device.id),
            details=f"Trusted device created: {trusted_device.device_name}",
            changes={
                "device_id": trusted_device.id,
                "device_name": trusted_device.device_name,
                "ip_address": trusted_device.ip_address,
                "location": trusted_device.location
            }
        )
        
        return trusted_device
    
    async def verify_trusted_device(
        self, 
        db: AsyncSession, 
        token: str, 
        request: Request,
        user_id: int
    ) -> Optional[TrustedDevice]:
        """
        Verify a trusted device token
        
        Args:
            db: Database session
            token: Trusted device token
            request: FastAPI request object
            user_id: User ID
            
        Returns:
            TrustedDevice if valid, None otherwise
        """
        # Hash the provided token
        token_hash = self.hash_token(token)
        
        # Get device info from request
        device_info = DeviceFingerprint.extract_device_info_from_request(request)
        
        # Find trusted device
        result = await db.execute(
            select(TrustedDevice).where(
                and_(
                    TrustedDevice.user_id == user_id,
                    TrustedDevice.token_hash == token_hash,
                    TrustedDevice.is_active == True
                )
            )
        )
        trusted_device = result.scalars().first()
        
        if not trusted_device:
            return None
        
        # Check if expired
        if trusted_device.is_expired():
            await self._deactivate_device(db, trusted_device.id, "expired")
            return None
        
        # Validate device fingerprint
        if not DeviceFingerprint.validate_device_fingerprint(
            trusted_device.device_hash, 
            device_info["device_hash"]
        ):
            await self._deactivate_device(db, trusted_device.id, "fingerprint_mismatch")
            return None
        
        # Check geographic restrictions
        if not await self._validate_geographic_access(db, trusted_device, device_info):
            await self._deactivate_device(db, trusted_device.id, "geographic_restriction")
            return None
        
        # Update last used timestamp
        trusted_device.last_used_at = datetime.now()
        await db.commit()
        
        # Log the usage
        await logging_service.log_audit_event(
            event_type="trusted_device_used",
            resource_type="trusted_device",
            action="verify",
            user_id=user_id,
            resource_id=str(trusted_device.id),
            details=f"Trusted device used: {trusted_device.device_name}",
            changes={
                "device_id": trusted_device.id,
                "device_name": trusted_device.device_name,
                "ip_address": device_info["ip_address"],
                "location": device_info["location"]
            }
        )
        
        return trusted_device
    
    async def get_user_trusted_devices(self, db: AsyncSession, user_id: int) -> List[TrustedDevice]:
        """Get all active trusted devices for a user"""
        result = await db.execute(
            select(TrustedDevice).where(
                and_(
                    TrustedDevice.user_id == user_id,
                    TrustedDevice.is_active == True
                )
            ).order_by(TrustedDevice.last_used_at.desc())
        )
        return result.scalars().all()
    
    async def revoke_trusted_device(self, db: AsyncSession, user_id: int, device_id: int) -> bool:
        """Revoke a specific trusted device"""
        result = await db.execute(
            select(TrustedDevice).where(
                and_(
                    TrustedDevice.id == device_id,
                    TrustedDevice.user_id == user_id
                )
            )
        )
        trusted_device = result.scalars().first()
        
        if not trusted_device:
            return False
        
        await self._deactivate_device(db, device_id, "user_revoked")
        return True
    
    async def revoke_all_trusted_devices(self, db: AsyncSession, user_id: int) -> int:
        """Revoke all trusted devices for a user"""
        result = await db.execute(
            select(TrustedDevice).where(
                and_(
                    TrustedDevice.user_id == user_id,
                    TrustedDevice.is_active == True
                )
            )
        )
        devices = result.scalars().all()
        
        count = 0
        for device in devices:
            await self._deactivate_device(db, device.id, "bulk_revoke")
            count += 1
        
        return count
    
    async def _enforce_device_limit(self, db: AsyncSession, user_id: int):
        """Enforce maximum number of trusted devices per user"""
        result = await db.execute(
            select(TrustedDevice).where(
                and_(
                    TrustedDevice.user_id == user_id,
                    TrustedDevice.is_active == True
                )
            )
        )
        active_devices = result.scalars().all()
        
        if len(active_devices) >= self.max_devices_per_user:
            # Remove oldest device
            oldest_device = min(active_devices, key=lambda d: d.last_used_at)
            await self._deactivate_device(db, oldest_device.id, "device_limit_exceeded")
    
    async def _cleanup_expired_devices(self, db: AsyncSession, user_id: int):
        """Clean up expired trusted devices"""
        result = await db.execute(
            select(TrustedDevice).where(
                and_(
                    TrustedDevice.user_id == user_id,
                    TrustedDevice.is_active == True,
                    TrustedDevice.expires_at < datetime.now()
                )
            )
        )
        expired_devices = result.scalars().all()
        
        for device in expired_devices:
            await self._deactivate_device(db, device.id, "expired")
    
    async def _deactivate_device(self, db: AsyncSession, device_id: int, reason: str):
        """Deactivate a trusted device"""
        result = await db.execute(
            select(TrustedDevice).where(TrustedDevice.id == device_id)
        )
        device = result.scalars().first()
        
        if device:
            device.is_active = False
            await db.commit()
            
            # Log the deactivation
            await logging_service.log_audit_event(
                event_type="trusted_device_deactivated",
                resource_type="trusted_device",
                action="deactivate",
                user_id=device.user_id,
                resource_id=str(device.id),
                details=f"Trusted device deactivated: {device.device_name} - Reason: {reason}",
                changes={
                    "device_id": device.id,
                    "device_name": device.device_name,
                    "reason": reason
                }
            )
    
    async def _validate_geographic_access(
        self, 
        db: AsyncSession, 
        trusted_device: TrustedDevice, 
        current_device_info: Dict[str, Any]
    ) -> bool:
        """Validate geographic access restrictions"""
        # For now, allow access from same country or unknown locations
        # In production, implement more sophisticated geographic restrictions
        
        if trusted_device.country_code == "XX" or current_device_info["country_code"] == "XX":
            return True
        
        return trusted_device.country_code == current_device_info["country_code"]

# Global instance
trusted_device_service = TrustedDeviceService() 