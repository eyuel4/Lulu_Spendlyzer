import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from datetime import datetime, timedelta
import redis
import json

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        # Email configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL")
        
        # SMS configuration (Twilio)
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        # Redis for rate limiting and code storage
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=True
        )
        
        # Rate limiting settings
        self.sms_rate_limit = 5  # max SMS per hour per phone
        self.email_rate_limit = 10  # max emails per hour per email
        self.code_expiry = 300  # 5 minutes

    def send_email(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send email using SMTP"""
        try:
            if not all([self.smtp_username, self.smtp_password, self.from_email]):
                logger.error("Email configuration incomplete")
                return False
            
            # Check rate limit
            if not self._check_email_rate_limit(to_email):
                logger.warning(f"Email rate limit exceeded for {to_email}")
                return False
            
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add plain text
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Add HTML if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def send_sms(self, to_phone: str, message: str) -> bool:
        """Send SMS using Twilio"""
        try:
            if not all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_phone_number]):
                logger.error("SMS configuration incomplete")
                return False
            
            # Check rate limit
            if not self._check_sms_rate_limit(to_phone):
                logger.warning(f"SMS rate limit exceeded for {to_phone}")
                return False
            
            # Format phone number
            formatted_phone = self._format_phone_number(to_phone)
            
            # Twilio API call
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
            payload = {
                'From': self.twilio_phone_number,
                'To': formatted_phone,
                'Body': message
            }
            
            response = requests.post(
                url,
                data=payload,
                auth=(self.twilio_account_sid, self.twilio_auth_token)
            )
            
            if response.status_code == 201:
                logger.info(f"SMS sent successfully to {formatted_phone}")
                return True
            else:
                logger.error(f"Twilio API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone}: {str(e)}")
            return False

    def generate_and_store_code(self, user_id: int, method: str, contact: str) -> Optional[str]:
        """Generate verification code and store it with expiry"""
        try:
            import secrets
            code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            
            # Store code in Redis with expiry
            key = f"2fa_code:{user_id}:{method}"
            code_data = {
                'code': code,
                'contact': contact,
                'created_at': datetime.utcnow().isoformat(),
                'attempts': 0
            }
            
            self.redis_client.setex(
                key,
                self.code_expiry,
                json.dumps(code_data)
            )
            
            logger.info(f"Generated 2FA code for user {user_id} via {method}")
            return code
            
        except Exception as e:
            logger.error(f"Failed to generate code for user {user_id}: {str(e)}")
            return None

    def verify_code(self, user_id: int, method: str, code: str) -> bool:
        """Verify 2FA code"""
        try:
            key = f"2fa_code:{user_id}:{method}"
            stored_data = self.redis_client.get(key)
            
            if not stored_data:
                return False
            
            code_data = json.loads(stored_data)
            
            # Check attempts
            if code_data['attempts'] >= 3:
                logger.warning(f"Too many attempts for user {user_id}")
                self.redis_client.delete(key)
                return False
            
            # Increment attempts
            code_data['attempts'] += 1
            self.redis_client.setex(key, self.code_expiry, json.dumps(code_data))
            
            # Verify code
            if code_data['code'] == code:
                # Delete code after successful verification
                self.redis_client.delete(key)
                logger.info(f"2FA code verified for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to verify code for user {user_id}: {str(e)}")
            return False

    def send_2fa_email(self, user_id: int, email: str) -> bool:
        """Send 2FA verification email"""
        try:
            code = self.generate_and_store_code(user_id, 'email', email)
            if not code:
                return False
            
            subject = "Your Spendlyzer Verification Code"
            body = f"""
            Your verification code is: {code}
            
            This code will expire in 5 minutes.
            
            If you didn't request this code, please ignore this email.
            
            Best regards,
            The Spendlyzer Team
            """
            
            html_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #4f46e5;">Spendlyzer Verification Code</h2>
                <p>Your verification code is:</p>
                <div style="background-color: #f3f4f6; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                    <span style="font-size: 24px; font-weight: bold; letter-spacing: 4px; color: #1f2937;">{code}</span>
                </div>
                <p style="color: #6b7280; font-size: 14px;">This code will expire in 5 minutes.</p>
                <p style="color: #6b7280; font-size: 14px;">If you didn't request this code, please ignore this email.</p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 12px;">Best regards,<br>The Spendlyzer Team</p>
            </div>
            """
            
            return self.send_email(email, subject, body, html_body)
            
        except Exception as e:
            logger.error(f"Failed to send 2FA email to {email}: {str(e)}")
            return False

    def send_2fa_sms(self, user_id: int, phone: str) -> bool:
        """Send 2FA verification SMS"""
        try:
            code = self.generate_and_store_code(user_id, 'sms', phone)
            if not code:
                return False
            
            message = f"Your Spendlyzer verification code is: {code}. This code expires in 5 minutes."
            
            return self.send_sms(phone, message)
            
        except Exception as e:
            logger.error(f"Failed to send 2FA SMS to {phone}: {str(e)}")
            return False

    def _check_email_rate_limit(self, email: str) -> bool:
        """Check email rate limit"""
        key = f"email_rate_limit:{email}"
        current_count = self.redis_client.get(key)
        
        if current_count and int(current_count) >= self.email_rate_limit:
            return False
        
        pipe = self.redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 3600)  # 1 hour
        pipe.execute()
        
        return True

    def _check_sms_rate_limit(self, phone: str) -> bool:
        """Check SMS rate limit"""
        key = f"sms_rate_limit:{phone}"
        current_count = self.redis_client.get(key)
        
        if current_count and int(current_count) >= self.sms_rate_limit:
            return False
        
        pipe = self.redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 3600)  # 1 hour
        pipe.execute()
        
        return True

    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for Twilio"""
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone))
        
        # Add +1 if it's a US number without country code
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"+{digits}"
        elif digits.startswith('+'):
            return digits
        else:
            return f"+{digits}"

# Global instance
notification_service = NotificationService() 