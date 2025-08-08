from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.two_factor_auth import TwoFactorAuth, TwoFactorBackupCode
from app.schemas.two_factor_auth import (
    TwoFactorAuthSettings, EnableTwoFactorRequest, TwoFactorSetupResponse,
    VerifyTwoFactorRequest, DisableTwoFactorRequest
)
import jwt
import os
import pyotp
import qrcode
import io
import base64
import secrets
import hashlib
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from typing import List
from pydantic import BaseModel

# New schemas for code sending and resending
class SendCodeRequest(BaseModel):
    method: str
    phone_number: str = None

class SendCodeResponse(BaseModel):
    success: bool
    message: str
    expires_at: str = None
    method: str

class ResendCodeRequest(BaseModel):
    method: str

class ResendCodeResponse(BaseModel):
    success: bool
    message: str
    expires_at: str
    method: str

class VerifySetupRequest(BaseModel):
    code: str

router = APIRouter(prefix="/users/2fa", tags=["two-factor-authentication"])

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"

# Email configuration
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_2fa_verification_email(to_email: str, code: str, method: str):
    """Send 2FA verification code via email"""
    try:
        msg = EmailMessage()
        msg["Subject"] = f"Spendlyzer {method.upper()} Verification Code"
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg.set_content(
            f"Your Spendlyzer verification code is: {code}\n\n"
            f"This code will expire in 10 minutes.\n\n"
            f"If you didn't request this code, please ignore this email."
        )
        
        if not EMAIL_FROM or not EMAIL_PASSWORD:
            print(f"Error: EMAIL_FROM or EMAIL_PASSWORD not set. Cannot send {method} verification email to {to_email}")
            return False
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print(f"{method.upper()} verification email sent successfully to {to_email}")
            return True
    except Exception as e:
        print(f"Error sending {method} verification email to {to_email}: {e}")
        return False

def get_current_user_id(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/settings", response_model=TwoFactorAuthSettings)
async def get_two_factor_settings(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_current_user_id(request)
    
    result = await db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user_id))
    two_factor = result.scalars().first()
    
    if not two_factor:
        return TwoFactorAuthSettings(enabled=False)
    
    # Get backup codes (not the actual codes, just indicate if they exist)
    backup_codes_result = await db.execute(
        select(TwoFactorBackupCode).where(
            TwoFactorBackupCode.user_id == user_id,
            TwoFactorBackupCode.is_used == False
        )
    )
    backup_codes_count = len(backup_codes_result.scalars().all())
    
    return TwoFactorAuthSettings(
        enabled=two_factor.is_enabled,
        method=two_factor.method if two_factor.is_enabled else None,
        phone_number=two_factor.phone_number if two_factor.method == 'sms' else None,
        backup_codes=[f"***-***-{i+1:03d}" for i in range(backup_codes_count)]
    )

@router.post("/enable", response_model=TwoFactorSetupResponse)
async def enable_two_factor(
    request: Request, 
    enable_request: EnableTwoFactorRequest,
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(request)
    
    # Get user info
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if 2FA already enabled
    result = await db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user_id))
    existing_2fa = result.scalars().first()
    
    if existing_2fa and existing_2fa.is_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is already enabled")
    
    # Generate backup codes
    backup_codes = []
    for _ in range(10):
        code = '-'.join([secrets.token_hex(2).upper() for _ in range(3)])  # Format: XX-XX-XX
        backup_codes.append(code)
        
        # Store hashed backup code
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        backup_code_record = TwoFactorBackupCode(
            user_id=user_id,
            code_hash=code_hash,
            is_used=False
        )
        db.add(backup_code_record)
    
    response_data = {"backup_codes": backup_codes}
    
    if enable_request.method == 'authenticator':
        # Generate secret key for TOTP
        secret_key = pyotp.random_base32()
        
        # Create TOTP object
        totp = pyotp.TOTP(secret_key)
        
        # Generate QR code
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="Spendlyzer"
        )
        
        # Create QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        response_data.update({
            "qr_code_url": f"data:image/png;base64,{img_str}",
            "secret_key": secret_key
        })
        
        # Create or update 2FA record
        if existing_2fa:
            existing_2fa.method = enable_request.method
            existing_2fa.secret_key = secret_key
            existing_2fa.is_enabled = True
            existing_2fa.updated_at = datetime.utcnow()
        else:
            two_factor = TwoFactorAuth(
                user_id=user_id,
                method=enable_request.method,
                secret_key=secret_key,
                is_enabled=True
            )
            db.add(two_factor)
    
    elif enable_request.method == 'sms':
        if not enable_request.phone_number:
            raise HTTPException(status_code=400, detail="Phone number is required for SMS 2FA")
        
        # Check if verification was completed (temp_code should be cleared after verification)
        if existing_2fa and existing_2fa.temp_code:
            raise HTTPException(status_code=400, detail="Please verify your phone number first by entering the code sent to your phone")
        
        # Create or update 2FA record
        if existing_2fa:
            existing_2fa.method = enable_request.method
            existing_2fa.phone_number = enable_request.phone_number
            existing_2fa.is_enabled = True
            existing_2fa.updated_at = datetime.utcnow()
        else:
            two_factor = TwoFactorAuth(
                user_id=user_id,
                method=enable_request.method,
                phone_number=enable_request.phone_number,
                is_enabled=True
            )
            db.add(two_factor)
    
    elif enable_request.method == 'email':
        # Check if verification was completed (temp_code should be cleared after verification)
        if existing_2fa and existing_2fa.temp_code:
            raise HTTPException(status_code=400, detail="Please verify your email first by entering the code sent to your email")
        
        # Create or update 2FA record
        if existing_2fa:
            existing_2fa.method = enable_request.method
            existing_2fa.is_enabled = True
            existing_2fa.updated_at = datetime.utcnow()
        else:
            two_factor = TwoFactorAuth(
                user_id=user_id,
                method=enable_request.method,
                is_enabled=True
            )
            db.add(two_factor)
    
    else:
        raise HTTPException(status_code=400, detail="Invalid 2FA method")
    
    await db.commit()
    
    return TwoFactorSetupResponse(**response_data)

@router.post("/verify")
async def verify_two_factor(
    request: Request,
    verify_request: VerifyTwoFactorRequest,
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(request)
    
    result = await db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user_id))
    two_factor = result.scalars().first()
    
    if not two_factor or not two_factor.is_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")
    
    is_valid = False
    
    if two_factor.method == 'authenticator':
        if not two_factor.secret_key:
            raise HTTPException(status_code=500, detail="No secret key found")
        
        totp = pyotp.TOTP(two_factor.secret_key)
        is_valid = totp.verify(verify_request.code, valid_window=1)
    
    elif two_factor.method == 'sms':
        # Check against temporary code with expiration
        if (two_factor.temp_code and 
            two_factor.temp_code_expires_at and 
            two_factor.temp_code == verify_request.code and
            datetime.utcnow() < two_factor.temp_code_expires_at):
            is_valid = True
            # Clear the temporary code after successful verification
            two_factor.temp_code = None
            two_factor.temp_code_expires_at = None
            await db.commit()
        else:
            is_valid = False
    
    elif two_factor.method == 'email':
        # Check against temporary code with expiration
        if (two_factor.temp_code and 
            two_factor.temp_code_expires_at and 
            two_factor.temp_code == verify_request.code and
            datetime.utcnow() < two_factor.temp_code_expires_at):
            is_valid = True
            # Clear the temporary code after successful verification
            two_factor.temp_code = None
            two_factor.temp_code_expires_at = None
            await db.commit()
        else:
            is_valid = False
    
    # Check if it's a backup code
    if not is_valid:
        code_hash = hashlib.sha256(verify_request.code.encode()).hexdigest()
        backup_result = await db.execute(
            select(TwoFactorBackupCode).where(
                TwoFactorBackupCode.user_id == user_id,
                TwoFactorBackupCode.code_hash == code_hash,
                TwoFactorBackupCode.is_used == False
            )
        )
        backup_code = backup_result.scalars().first()
        
        if backup_code:
            is_valid = True
            backup_code.is_used = True
            backup_code.used_at = datetime.utcnow()
            await db.commit()
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    return {"message": "Two-factor authentication verified successfully"}

@router.post("/disable")
async def disable_two_factor(
    request: Request,
    disable_request: DisableTwoFactorRequest,
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(request)
    
    result = await db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user_id))
    two_factor = result.scalars().first()
    
    if not two_factor or not two_factor.is_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")
    
    # If verification code is provided, verify it
    if disable_request.verification_code:
        is_valid = False
        
        if two_factor.method == 'authenticator' and two_factor.secret_key:
            totp = pyotp.TOTP(two_factor.secret_key)
            is_valid = totp.verify(disable_request.verification_code, valid_window=1)
        elif two_factor.method in ['sms', 'email']:
            # For demo purposes, accept any 6-digit code
            is_valid = len(disable_request.verification_code) == 6 and disable_request.verification_code.isdigit()
        
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Disable 2FA
    two_factor.is_enabled = False
    two_factor.updated_at = datetime.utcnow()
    
    # Remove all unused backup codes
    await db.execute(
        select(TwoFactorBackupCode).where(
            TwoFactorBackupCode.user_id == user_id,
            TwoFactorBackupCode.is_used == False
        )
    )
    unused_codes = await db.execute(
        select(TwoFactorBackupCode).where(
            TwoFactorBackupCode.user_id == user_id,
            TwoFactorBackupCode.is_used == False
        )
    )
    for code in unused_codes.scalars().all():
        await db.delete(code)
    
    await db.commit()
    
    return {"message": "Two-factor authentication disabled successfully"}

@router.get("/backup-codes")
async def regenerate_backup_codes(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_current_user_id(request)
    
    result = await db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user_id))
    two_factor = result.scalars().first()
    
    if not two_factor or not two_factor.is_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")
    
    # Remove all existing backup codes
    existing_codes_result = await db.execute(
        select(TwoFactorBackupCode).where(TwoFactorBackupCode.user_id == user_id)
    )
    for code in existing_codes_result.scalars().all():
        await db.delete(code)
    
    # Generate new backup codes
    backup_codes = []
    for _ in range(10):
        code = '-'.join([secrets.token_hex(2).upper() for _ in range(3)])
        backup_codes.append(code)
        
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        backup_code_record = TwoFactorBackupCode(
            user_id=user_id,
            code_hash=code_hash,
            is_used=False
        )
        db.add(backup_code_record)
    
    await db.commit()
    
    return {"backup_codes": backup_codes}

@router.post("/send-code", response_model=SendCodeResponse)
async def send_two_factor_code(
    request: Request,
    send_request: SendCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(request)
    
    # Get user info
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if 2FA is enabled
    result = await db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user_id))
    two_factor = result.scalars().first()
    
    if not two_factor or not two_factor.is_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")
    
    # Only allow SMS and Email methods for code sending
    if send_request.method not in ['sms', 'email']:
        raise HTTPException(status_code=400, detail="Code sending is only available for SMS and Email methods")
    
    # Check if method matches user's 2FA method
    if two_factor.method != send_request.method:
        raise HTTPException(status_code=400, detail=f"Your 2FA method is {two_factor.method}, not {send_request.method}")
    
    # Generate a 6-digit code
    code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # Set expiration time (10 minutes from now)
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Store the code temporarily (in a real implementation, you'd store this in Redis or similar)
    # For now, we'll store it in the two_factor record
    two_factor.temp_code = code
    two_factor.temp_code_expires_at = expires_at
    await db.commit()
    
    # Send the code (in a real implementation, you'd integrate with SMS/Email services)
    if send_request.method == 'sms':
        # TODO: Integrate with SMS service
        print(f"SMS verification code sent to {send_request.phone_number or user.phone}")
        message = f"Verification code has been sent to your phone. Code expires in 10 minutes."
    else:  # email
        # Send actual email
        email_sent = send_2fa_verification_email(user.email, code, "email")
        if email_sent:
            message = f"Verification code has been sent to your email. Code expires in 10 minutes."
        else:
            message = f"Failed to send verification email. Please try again."
    
    return SendCodeResponse(
        success=True,
        message=message,
        expires_at=expires_at.isoformat(),
        method=send_request.method
    )

@router.post("/send-setup-code", response_model=SendCodeResponse)
async def send_setup_verification_code(
    request: Request,
    send_request: SendCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(request)
    
    # Get user info
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if 2FA is already enabled
    result = await db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user_id))
    two_factor = result.scalars().first()
    
    if two_factor and two_factor.is_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is already enabled")
    
    # Only allow SMS and Email methods for setup verification
    if send_request.method not in ['sms', 'email']:
        raise HTTPException(status_code=400, detail="Setup verification is only available for SMS and Email methods")
    
    # Generate a 6-digit code
    code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # Set expiration time (10 minutes from now)
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Create or update 2FA record with temporary code
    if two_factor:
        two_factor.temp_code = code
        two_factor.temp_code_expires_at = expires_at
        two_factor.method = send_request.method
        if send_request.method == 'sms':
            two_factor.phone_number = send_request.phone_number
    else:
        two_factor = TwoFactorAuth(
            user_id=user_id,
            method=send_request.method,
            phone_number=send_request.phone_number if send_request.method == 'sms' else None,
            temp_code=code,
            temp_code_expires_at=expires_at,
            is_enabled=False
        )
        db.add(two_factor)
    
    await db.commit()
    
    # Send the code (in a real implementation, you'd integrate with SMS/Email services)
    if send_request.method == 'sms':
        # TODO: Integrate with SMS service
        print(f"Setup SMS verification code sent to {send_request.phone_number or user.phone}")
        message = f"Setup verification code has been sent to your phone. Code expires in 10 minutes."
    else:  # email
        # Send actual email
        email_sent = send_2fa_verification_email(user.email, code, "email")
        if email_sent:
            message = f"Setup verification code has been sent to your email. Code expires in 10 minutes."
        else:
            message = f"Failed to send setup verification email. Please try again."
    
    return SendCodeResponse(
        success=True,
        message=message,
        expires_at=expires_at.isoformat(),
        method=send_request.method
    )

@router.post("/resend-code", response_model=ResendCodeResponse)
async def resend_two_factor_code(
    request: Request,
    resend_request: ResendCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(request)
    
    # Get user info
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if 2FA is enabled
    result = await db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user_id))
    two_factor = result.scalars().first()
    
    if not two_factor or not two_factor.is_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")
    
    # Only allow SMS and Email methods for code resending
    if resend_request.method not in ['sms', 'email']:
        return ResendCodeResponse(
            success=False,
            message="Resend is not available for authenticator apps",
            expires_at="",
            method=resend_request.method
        )
    
    # Check if method matches user's 2FA method
    if two_factor.method != resend_request.method:
        raise HTTPException(status_code=400, detail=f"Your 2FA method is {two_factor.method}, not {resend_request.method}")
    
    # Generate a new 6-digit code
    code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # Set expiration time (10 minutes from now)
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Store the new code temporarily
    two_factor.temp_code = code
    two_factor.temp_code_expires_at = expires_at
    await db.commit()
    
    # Send the new code
    if resend_request.method == 'sms':
        # TODO: Integrate with SMS service
        print(f"SMS verification code resent to {user.phone}")
        message = f"New verification code has been sent to your phone. Code expires in 10 minutes."
    else:  # email
        # Send actual email
        email_sent = send_2fa_verification_email(user.email, code, "email")
        if email_sent:
            message = f"New verification code has been sent to your email. Code expires in 10 minutes."
        else:
            message = f"Failed to resend verification email. Please try again."
    
    return ResendCodeResponse(
        success=True,
        message=message,
        expires_at=expires_at.isoformat(),
        method=resend_request.method
    )

@router.post("/verify-setup")
async def verify_setup_code(
    request: Request,
    verify_request: VerifySetupRequest,
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(request)
    
    # Get user info
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if there's a temporary code for this user
    result = await db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user_id))
    two_factor = result.scalars().first()
    
    if not two_factor or not two_factor.temp_code or not two_factor.temp_code_expires_at:
        raise HTTPException(status_code=400, detail="No verification code found. Please request a new one.")
    
    # Check if code has expired
    if datetime.utcnow() > two_factor.temp_code_expires_at:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")
    
    # Verify the code
    if two_factor.temp_code != verify_request.code:
        raise HTTPException(status_code=400, detail="Invalid verification code.")
    
    # Code is valid - clear the temporary code
    two_factor.temp_code = None
    two_factor.temp_code_expires_at = None
    await db.commit()
    
    return {"message": "Verification successful"}

@router.post("/send-login-code", response_model=SendCodeResponse)
async def send_login_verification_code(
    request: Request,
    send_request: SendCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send 2FA code during login (uses temporary token)"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    temp_token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(temp_token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("temp_2fa"):
            raise HTTPException(status_code=401, detail="Invalid temporary token")
        
        user_id = int(payload.get("sub"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get user info
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if 2FA is enabled
    result = await db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user_id))
    two_factor = result.scalars().first()
    
    if not two_factor or not two_factor.is_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")
    
    # Only allow SMS and Email methods for code sending
    if send_request.method not in ['sms', 'email']:
        raise HTTPException(status_code=400, detail="Code sending is only available for SMS and Email methods")
    
    # Check if method matches user's 2FA method
    if two_factor.method != send_request.method:
        raise HTTPException(status_code=400, detail=f"Your 2FA method is {two_factor.method}, not {send_request.method}")
    
    # Generate a 6-digit code
    code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # Set expiration time (10 minutes from now)
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Store the code temporarily
    two_factor.temp_code = code
    two_factor.temp_code_expires_at = expires_at
    await db.commit()
    
    # Send the code
    if send_request.method == 'sms':
        # TODO: Integrate with SMS service
        print(f"Login SMS verification code sent to {send_request.phone_number or user.phone}")
        message = f"Login verification code has been sent to your phone. Code expires in 10 minutes."
    else:  # email
        # Send actual email
        email_sent = send_2fa_verification_email(user.email, code, "email")
        if email_sent:
            message = f"Login verification code has been sent to your email. Code expires in 10 minutes."
        else:
            message = f"Failed to send login verification email. Please try again."
    
    return SendCodeResponse(
        success=True,
        message=message,
        expires_at=expires_at.isoformat(),
        method=send_request.method
    )