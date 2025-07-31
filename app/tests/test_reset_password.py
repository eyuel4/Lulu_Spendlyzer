#!/usr/bin/env python3
"""
Unit tests for reset password functionality in Spendlyzer
Tests both forgot-password and reset-password endpoints.
"""

import os
import sys
import pytest
import jwt
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db
from app.models.user import User as UserModel
from app.routes.auth import create_reset_token, hash_password, verify_password

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_finance.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestResetPassword:
    """Test cases for reset password functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Setup test database and create test user"""
        # Create tables
        from app.models.base import Base
        Base.metadata.create_all(bind=engine)
        
        # Create test user
        db = TestingSessionLocal()
        test_user = UserModel(
            first_name="Test",
            last_name="User",
            username="testuser",
            email="test@example.com",
            password_hash=hash_password("oldpassword123"),
            is_primary=True,
            created_at=datetime.now(timezone.utc)
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        self.test_user = test_user
        self.test_user_id = test_user.id
        
        yield
        
        # Cleanup
        db.close()
        # Remove test database
        if os.path.exists("./test_finance.db"):
            os.remove("./test_finance.db")
    
    def test_forgot_password_success(self):
        """Test successful forgot password request"""
        client = TestClient(app)
        
        response = client.post("/auth/forgot-password", json={
            "email": "test@example.com"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "If the email is registered" in data["message"]
    
    def test_forgot_password_invalid_email(self):
        """Test forgot password with non-existent email"""
        client = TestClient(app)
        
        response = client.post("/auth/forgot-password", json={
            "email": "nonexistent@example.com"
        })
        
        # Should still return 200 for security reasons
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "If the email is registered" in data["message"]
    
    def test_forgot_password_invalid_payload(self):
        """Test forgot password with invalid payload"""
        client = TestClient(app)
        
        # Missing email
        response = client.post("/auth/forgot-password", json={})
        assert response.status_code == 422
        
        # Invalid email format
        response = client.post("/auth/forgot-password", json={
            "email": "invalid-email"
        })
        assert response.status_code == 422
    
    def test_reset_password_success(self):
        """Test successful password reset"""
        client = TestClient(app)
        
        # Create a valid reset token
        token = create_reset_token(self.test_user_id, "test@example.com")
        
        response = client.post("/auth/reset-password", json={
            "token": token,
            "new_password": "newpassword123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Password reset successful" in data["message"]
        
        # Verify password was actually changed
        db = TestingSessionLocal()
        updated_user = db.query(UserModel).filter(UserModel.id == self.test_user_id).first()
        db.close()
        
        assert verify_password("newpassword123", updated_user.password_hash)
        assert not verify_password("oldpassword123", updated_user.password_hash)
    
    def test_reset_password_invalid_token(self):
        """Test password reset with invalid token"""
        client = TestClient(app)
        
        response = client.post("/auth/reset-password", json={
            "token": "invalid-token",
            "new_password": "newpassword123"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid token" in data["detail"]
    
    def test_reset_password_expired_token(self):
        """Test password reset with expired token"""
        client = TestClient(app)
        
        # Create an expired token (manually create one with short expiry)
        from app.routes.auth import SECRET_KEY, ALGORITHM
        expired_token = jwt.encode(
            {
                "sub": str(self.test_user_id),
                "email": "test@example.com",
                "reset": True,
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1)  # Expired 1 minute ago
            },
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        
        response = client.post("/auth/reset-password", json={
            "token": expired_token,
            "new_password": "newpassword123"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Reset token expired" in data["detail"]
    
    def test_reset_password_token_without_reset_flag(self):
        """Test password reset with token that doesn't have reset flag"""
        client = TestClient(app)
        
        # Create a token without the reset flag
        from app.routes.auth import SECRET_KEY, ALGORITHM
        invalid_token = jwt.encode(
            {
                "sub": str(self.test_user_id),
                "email": "test@example.com",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
            },
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        
        response = client.post("/auth/reset-password", json={
            "token": invalid_token,
            "new_password": "newpassword123"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid token" in data["detail"]
    
    def test_reset_password_user_not_found(self):
        """Test password reset with token for non-existent user"""
        client = TestClient(app)
        
        # Create token for non-existent user
        token = create_reset_token(99999, "nonexistent@example.com")
        
        response = client.post("/auth/reset-password", json={
            "token": token,
            "new_password": "newpassword123"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid token" in data["detail"]
    
    def test_reset_password_invalid_payload(self):
        """Test password reset with invalid payload"""
        client = TestClient(app)
        
        # Missing token
        response = client.post("/auth/reset-password", json={
            "new_password": "newpassword123"
        })
        assert response.status_code == 422
        
        # Missing new_password
        response = client.post("/auth/reset-password", json={
            "token": "some-token"
        })
        assert response.status_code == 422
        
        # Empty payload
        response = client.post("/auth/reset-password", json={})
        assert response.status_code == 422
    
    def test_reset_password_short_password(self):
        """Test password reset with password that's too short"""
        client = TestClient(app)
        
        token = create_reset_token(self.test_user_id, "test@example.com")
        
        response = client.post("/auth/reset-password", json={
            "token": token,
            "new_password": "123"  # Too short
        })
        
        # This should still work as the backend doesn't validate password length
        # The frontend should handle this validation
        assert response.status_code == 200
    
    @patch('app.routes.auth.send_reset_email')
    def test_forgot_password_sends_email(self, mock_send_email):
        """Test that forgot password actually sends an email"""
        client = TestClient(app)
        
        response = client.post("/auth/forgot-password", json={
            "email": "test@example.com"
        })
        
        assert response.status_code == 200
        
        # Verify email sending was called
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args
        assert call_args[0][0] == "test@example.com"  # email
        assert "reset-password?token=" in call_args[0][1]  # reset_link
    
    def test_create_reset_token(self):
        """Test reset token creation"""
        token = create_reset_token(self.test_user_id, "test@example.com")
        
        # Decode and verify token
        from app.routes.auth import SECRET_KEY, ALGORITHM
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert decoded["sub"] == str(self.test_user_id)
        assert decoded["email"] == "test@example.com"
        assert decoded["reset"] is True
        assert "exp" in decoded
    
    def test_reset_password_flow_integration(self):
        """Test complete reset password flow"""
        client = TestClient(app)
        
        # Step 1: Request password reset
        response = client.post("/auth/forgot-password", json={
            "email": "test@example.com"
        })
        assert response.status_code == 200
        
        # Step 2: Create reset token (simulating email link)
        token = create_reset_token(self.test_user_id, "test@example.com")
        
        # Step 3: Reset password
        response = client.post("/auth/reset-password", json={
            "token": token,
            "new_password": "newsecurepassword456"
        })
        assert response.status_code == 200
        
        # Step 4: Verify password was changed
        db = TestingSessionLocal()
        updated_user = db.query(UserModel).filter(UserModel.id == self.test_user_id).first()
        db.close()
        
        assert verify_password("newsecurepassword456", updated_user.password_hash)
        assert not verify_password("oldpassword123", updated_user.password_hash)

def run_reset_password_tests():
    """Run all reset password tests"""
    print("🧪 Running Reset Password Tests")
    print("=" * 50)
    
    # Run tests with pytest
    result = pytest.main([
        str(Path(__file__)),
        "-v",
        "--tb=short"
    ])
    
    print("\n" + "=" * 50)
    if result == 0:
        print("✅ All reset password tests passed!")
    else:
        print("❌ Some reset password tests failed. Check the output above.")
    
    return result == 0

if __name__ == "__main__":
    success = run_reset_password_tests()
    sys.exit(0 if success else 1) 