#!/usr/bin/env python3
"""
Unit test for email functionality in Spendlyzer
Tests the send_invitation_email function and validates email sending works correctly.
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Try app directory
    app_env_path = project_root / 'app' / '.env'
    if app_env_path.exists():
        load_dotenv(dotenv_path=app_env_path)

# Import the email function
from app.routes.auth import send_invitation_email

class TestEmailFunctionality(unittest.TestCase):
    """Test cases for email functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_email = "test@example.com"
        self.test_first_name = "Test"
        self.test_token = "test_token_12345"
        
        # Check if email configuration is set
        self.email_from = os.getenv('EMAIL_FROM')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        
        if not self.email_from or not self.email_password:
            print("⚠️  Warning: EMAIL_FROM or EMAIL_PASSWORD not set in .env file")
            print("   Email tests will be skipped. Please configure email settings first.")
    
    def test_email_configuration(self):
        """Test that email configuration is properly set"""
        if not self.email_from or not self.email_password:
            self.skipTest("Email configuration not set")
        
        self.assertIsNotNone(self.email_from, "EMAIL_FROM should be set")
        self.assertIsNotNone(self.email_password, "EMAIL_PASSWORD should be set")
        self.assertIn("@", self.email_from, "EMAIL_FROM should be a valid email")
        self.assertEqual(len(self.email_password), 16, "EMAIL_PASSWORD should be 16 characters (App Password)")
        
        print(f"✅ Email configuration validated:")
        print(f"   From: {self.email_from}")
        print(f"   Password length: {len(self.email_password)} characters")
    
    @patch('smtplib.SMTP_SSL')
    def test_send_invitation_email_mock(self, mock_smtp):
        """Test email sending with mocked SMTP"""
        # Set up mock
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        
        # Call the function
        send_invitation_email(self.test_email, self.test_first_name, self.test_token)
        
        # Verify SMTP was called correctly
        mock_smtp.assert_called_once_with("smtp.gmail.com", 465)
        mock_smtp_instance.login.assert_called_once_with(self.email_from, self.email_password)
        mock_smtp_instance.send_message.assert_called_once()
        
        # Verify email content
        sent_message = mock_smtp_instance.send_message.call_args[0][0]
        self.assertEqual(sent_message["Subject"], "You're invited to join a Family Group on Spendlyzer!")
        self.assertEqual(sent_message["From"], self.email_from)
        self.assertEqual(sent_message["To"], self.test_email)
        
        # Check that the signup link is in the content
        content = sent_message.get_content()
        expected_link = f"http://localhost:4200/invite-signup?token={self.test_token}"
        self.assertIn(expected_link, content)
        self.assertIn(self.test_first_name, content)
        
        print("✅ Mock email test passed")
    
    def test_send_invitation_email_real(self):
        """Test actual email sending (requires valid email config)"""
        if not self.email_from or not self.email_password:
            self.skipTest("Email configuration not set")
        
        # Hardcoded test email
        test_email = "eyuel4@yahoo.com"
        
        print(f"📧 Sending test invitation email to {test_email}...")
        
        try:
            # Send the email
            send_invitation_email(test_email, self.test_first_name, self.test_token)
            print("✅ Test email sent successfully!")
            print(f"   Check {test_email} for the invitation email")
            print(f"   Signup link: http://localhost:4200/invite-signup?token={self.test_token}")
            
        except Exception as e:
            self.fail(f"Failed to send test email: {e}")
    
    def test_email_content_validation(self):
        """Test email content structure and format"""
        # Test with different inputs
        test_cases = [
            {
                "email": "user1@example.com",
                "first_name": "John",
                "token": "token123",
                "expected_link": "http://localhost:4200/invite-signup?token=token123"
            },
            {
                "email": "user2@test.org",
                "first_name": "Jane",
                "token": "abc123def456",
                "expected_link": "http://localhost:4200/invite-signup?token=abc123def456"
            }
        ]
        
        for case in test_cases:
            with self.subTest(email=case["email"]):
                # Mock SMTP to capture email content
                with patch('smtplib.SMTP_SSL') as mock_smtp:
                    mock_smtp_instance = MagicMock()
                    mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
                    
                    # Send email
                    send_invitation_email(case["email"], case["first_name"], case["token"])
                    
                    # Verify email structure
                    sent_message = mock_smtp_instance.send_message.call_args[0][0]
                    
                    # Check headers
                    self.assertEqual(sent_message["Subject"], "You're invited to join a Family Group on Spendlyzer!")
                    self.assertEqual(sent_message["To"], case["email"])
                    
                    # Check content
                    content = sent_message.get_content()
                    self.assertIn(case["expected_link"], content)
                    self.assertIn(case["first_name"], content)
                    self.assertIn("Spendlyzer", content)
                    self.assertIn("invitation", content.lower())
        
        print("✅ Email content validation passed")
    
    def test_email_error_handling(self):
        """Test email error handling"""
        # Test with invalid email configuration
        with patch.dict(os.environ, {'EMAIL_FROM': '', 'EMAIL_PASSWORD': ''}):
            # Should not raise exception, just return
            try:
                send_invitation_email(self.test_email, self.test_first_name, self.test_token)
                print("✅ Error handling test passed - function handled missing config gracefully")
            except Exception as e:
                self.fail(f"Function should handle missing email config gracefully: {e}")
        
        # Test with SMTP error
        with patch('smtplib.SMTP_SSL') as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP connection failed")
            
            # Should not raise exception, just log error
            try:
                send_invitation_email(self.test_email, self.test_first_name, self.test_token)
                print("✅ Error handling test passed - function handled SMTP error gracefully")
            except Exception as e:
                self.fail(f"Function should handle SMTP errors gracefully: {e}")

def run_email_tests():
    """Run all email tests"""
    print("🧪 Running Email Functionality Tests")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestEmailFunctionality)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All email tests passed!")
    else:
        print("❌ Some email tests failed. Check the output above.")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_email_tests()
    sys.exit(0 if success else 1) 