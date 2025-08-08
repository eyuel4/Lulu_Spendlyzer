import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from app.core.database import get_db
from app.models.user import User
from app.models.trusted_device import TrustedDevice
from app.models.two_factor_auth import TwoFactorAuth
from app.services.trusted_device_service import trusted_device_service
from app.core.device_fingerprint import DeviceFingerprint


class TestRememberDevice:
    """Test suite for Remember Device functionality"""
    
    @pytest.fixture
    async def db_session(self):
        """Provide database session for tests"""
        async for db in get_db():
            yield db
            await db.close()
    
    @pytest.fixture
    async def test_user(self, db_session):
        """Create a test user for testing"""
        from sqlalchemy import select
        
        # Check if test user exists
        result = await db_session.execute(
            select(User).where(User.email == "test@example.com")
        )
        user = result.scalars().first()
        
        if not user:
            # Create test user
            user = User(
                first_name="Test",
                last_name="User",
                username="testuser",
                email="test@example.com",
                password_hash="hashed_password",
                is_primary=True,
                auth_provider="password",
                is_verified=True
            )
            db_session.add(user)
            await db_session.commit()
            await db_session.refresh(user)
        
        return user
    
    @pytest.fixture
    async def test_2fa_settings(self, db_session, test_user):
        """Create 2FA settings for test user"""
        from sqlalchemy import select
        
        # Check if 2FA settings exist
        result = await db_session.execute(
            select(TwoFactorAuth).where(TwoFactorAuth.user_id == test_user.id)
        )
        two_factor = result.scalars().first()
        
        if not two_factor:
            # Create 2FA settings
            two_factor = TwoFactorAuth(
                user_id=test_user.id,
                is_enabled=True,
                method="email",
                secret_key="test_secret_key"
            )
            db_session.add(two_factor)
            await db_session.commit()
            await db_session.refresh(two_factor)
        
        return two_factor
    
    async def test_trusted_device_creation(self, db_session, test_user):
        """Test creating a trusted device"""
        # Mock request
        mock_request = Mock()
        mock_request.headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        mock_request.client.host = "127.0.0.1"
        
        # Create trusted device
        trusted_device_data = trusted_device_service.create_trusted_device(
            user_id=test_user.id,
            request=mock_request,
            remember_device=True,
            expiration_days=7
        )
        
        assert trusted_device_data is not None
        assert "trusted_device" in trusted_device_data
        assert "token" in trusted_device_data
        
        # Save to database
        trusted_device = await trusted_device_service.save_trusted_device(
            db_session, 
            trusted_device_data["trusted_device"]
        )
        
        assert trusted_device is not None
        assert trusted_device.user_id == test_user.id
        assert trusted_device.is_active is True
    
    async def test_trusted_device_verification(self, db_session, test_user, test_2fa_settings):
        """Test verifying a trusted device"""
        # Mock request
        mock_request = Mock()
        mock_request.headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        mock_request.client.host = "127.0.0.1"
        
        # Create trusted device first
        trusted_device_data = trusted_device_service.create_trusted_device(
            user_id=test_user.id,
            request=mock_request,
            remember_device=True,
            expiration_days=7
        )
        
        trusted_device = await trusted_device_service.save_trusted_device(
            db_session, 
            trusted_device_data["trusted_device"]
        )
        
        # Verify the trusted device
        verified_device = await trusted_device_service.verify_trusted_device(
            db=db_session,
            token=trusted_device_data["token"],
            request=mock_request,
            user_id=test_user.id
        )
        
        assert verified_device is not None
        assert verified_device.id == trusted_device.id
    
    async def test_trusted_device_expiration(self, db_session, test_user):
        """Test that expired trusted devices are not valid"""
        # Mock request
        mock_request = Mock()
        mock_request.headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        mock_request.client.host = "127.0.0.1"
        
        # Create trusted device with short expiration
        trusted_device_data = trusted_device_service.create_trusted_device(
            user_id=test_user.id,
            request=mock_request,
            remember_device=True,
            expiration_days=0  # Expires immediately
        )
        
        trusted_device = await trusted_device_service.save_trusted_device(
            db_session, 
            trusted_device_data["trusted_device"]
        )
        
        # Verify the trusted device should fail
        verified_device = await trusted_device_service.verify_trusted_device(
            db=db_session,
            token=trusted_device_data["token"],
            request=mock_request,
            user_id=test_user.id
        )
        
        assert verified_device is None
    
    async def test_device_fingerprint_creation(self):
        """Test device fingerprint creation"""
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        
        device_hash = DeviceFingerprint.create_device_hash(user_agent)
        
        assert device_hash is not None
        assert len(device_hash) == 64  # SHA-256 hash length
        
        device_name = DeviceFingerprint.get_device_name(user_agent)
        
        assert device_name is not None
        assert "Desktop" in device_name
        assert "Windows" in device_name
    
    async def test_trusted_device_cleanup(self, db_session, test_user):
        """Test cleanup of expired trusted devices"""
        # Create multiple trusted devices, some expired
        mock_request = Mock()
        mock_request.headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        mock_request.client.host = "127.0.0.1"
        
        # Create active device
        active_device_data = trusted_device_service.create_trusted_device(
            user_id=test_user.id,
            request=mock_request,
            remember_device=True,
            expiration_days=7
        )
        active_device = await trusted_device_service.save_trusted_device(
            db_session, 
            active_device_data["trusted_device"]
        )
        
        # Create expired device manually
        expired_device = TrustedDevice(
            user_id=test_user.id,
            device_hash="expired_hash",
            token_hash="expired_token_hash",
            device_name="Expired Device",
            user_agent="expired_agent",
            ip_address="127.0.0.1",
            location="Test Location",
            country_code="US",
            is_active=True,
            expires_at=TrustedDevice.create_expiration_date(days=-1)  # Expired yesterday
        )
        db_session.add(expired_device)
        await db_session.commit()
        
        # Run cleanup
        await trusted_device_service.cleanup_expired_devices(db_session)
        
        # Check that expired device is deactivated
        await db_session.refresh(expired_device)
        assert expired_device.is_active is False
        
        # Check that active device is still active
        await db_session.refresh(active_device)
        assert active_device.is_active is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 