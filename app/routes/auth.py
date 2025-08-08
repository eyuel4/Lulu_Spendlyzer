from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.database import get_db
from app.core.cache import get_cache, CacheKeys, RedisCache
from app.schemas.user import UserAuth, UserCreate, UserRead
from pydantic import BaseModel
from typing import List
from app.models.user import User as UserModel, UserPreferences as UserPreferencesModel
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import jwt
import os
import smtplib
from email.message import EmailMessage
from app.models.family_group import FamilyGroup
from app.models.invitation import Invitation
import secrets
from typing import cast
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import CookieTransport, AuthenticationBackend, JWTStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from authlib.integrations.starlette_client import OAuth
from fastapi_users.manager import BaseUserManager
from sqlalchemy import select
from app.schemas.family_group import FamilyGroupSetupRequest
from starlette.responses import RedirectResponse
import uuid
from app.models.user_session import UserSession
from app.models.two_factor_auth import TwoFactorAuth
from app.services.notification_service import notification_service
from sqlalchemy import select
import pyotp
import hashlib

SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET environment variable must be set")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
RESET_TOKEN_EXPIRE_MINUTES = 30

EMAIL_FROM = os.getenv("EMAIL_FROM")
if not EMAIL_FROM:
    raise RuntimeError("EMAIL_FROM environment variable must be set")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
if not EMAIL_PASSWORD:
    raise RuntimeError("EMAIL_PASSWORD environment variable must be set")
EMAIL_TO = os.getenv("EMAIL_TO")
if not EMAIL_TO:
    raise RuntimeError("EMAIL_TO environment variable must be set")

SECRET = os.getenv("JWT_SECRET")
if not SECRET:
    raise RuntimeError("JWT_SECRET environment variable must be set")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
if not GOOGLE_CLIENT_ID:
    raise RuntimeError("GOOGLE_CLIENT_ID environment variable must be set")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
if not GOOGLE_CLIENT_SECRET:
    raise RuntimeError("GOOGLE_CLIENT_SECRET environment variable must be set")

print("GOOGLE_CLIENT_ID:", repr(GOOGLE_CLIENT_ID))
print("GOOGLE_CLIENT_SECRET:", repr(GOOGLE_CLIENT_SECRET))
print("DB_URL:", os.getenv("DB_URL"))

router = APIRouter(prefix="/auth", tags=["auth"])

class UserPreferences(BaseModel):
    account_type: str
    primary_goal: List[str]
    financial_focus: List[str]
    experience_level: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class TwoFactorVerificationRequest(BaseModel):
    code: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, user: UserModel | None = None, expires_delta: timedelta | None = None, jti: str | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    if user is not None:
        to_encode.update({"exp": expire, "token_version": user.token_version})
    else:
        to_encode.update({"exp": expire})
    if jti is not None:
        to_encode["jti"] = jti
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # type: ignore
    return encoded_jwt

def create_reset_token(user_id: int, email: str):
    expire = timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    return create_access_token({"sub": str(user_id), "email": email, "reset": True}, expires_delta=expire)

def send_reset_email(to_email: str, reset_link: str):
    msg = EmailMessage()
    msg["Subject"] = "Password Reset Request"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    msg.set_content(f"Click the link to reset your password: {reset_link}\nIf you did not request this, ignore this email.")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        if not EMAIL_FROM or not EMAIL_PASSWORD:
            raise RuntimeError("EMAIL_FROM and EMAIL_PASSWORD must be set")
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.send_message(msg)

def send_invitation_email(to_email: str, first_name: str, signup_token: str):
    try:
        signup_link = f"http://localhost:4200/invite-signup?token={signup_token}"
        msg = EmailMessage()
        msg["Subject"] = "You're invited to join a Family Group on Spendlyzer!"
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg.set_content(
            f"Hi {first_name},\n\nYou have been invited to join a family group on Spendlyzer. "
            f"Click the link below to complete your signup process:\n{signup_link}\n\nIf you did not expect this invitation, you can ignore this email."
        )
        if not EMAIL_FROM or not EMAIL_PASSWORD:
            print(f"Error: EMAIL_FROM or EMAIL_PASSWORD not set. Cannot send email to {to_email}")
            return
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print(f"Invitation email sent successfully to {to_email}")
    except Exception as e:
        print(f"Error sending invitation email to {to_email}: {e}")
        # Don't raise the exception to avoid breaking the main flow

@router.post("/forgot-password")
async def forgot_password(
    background_tasks: BackgroundTasks,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    email = payload.email
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    user = result.scalars().first()
    # Always return success message, even if user not found
    if user:
        token = create_reset_token(cast(int, user.id), cast(str, user.email))
        reset_link = f"http://localhost:4200/reset-password?token={token}"
        background_tasks.add_task(send_reset_email, cast(str, user.email), reset_link)
    return {"message": "If the email is registered, a password reset link has been sent."}

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    token = payload.token
    new_password = payload.new_password
    try:
        decoded_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        if not decoded_payload.get("reset"):
            raise HTTPException(status_code=400, detail="Invalid token.")
        user_id = int(decoded_payload.get("sub"))
        email = decoded_payload.get("email")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Reset token expired.")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid token.")
    result = await db.execute(select(UserModel).where(UserModel.id == user_id, UserModel.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token.")
    user.password_hash = hash_password(new_password)  # type: ignore
    setattr(user, 'token_version', int(getattr(user, 'token_version', 0)) + 1)  # Invalidate all previous tokens
    await db.commit()
    return {"message": "Password reset successful."}

@router.post("/signup")
async def signup(user: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).where(UserModel.username == user.username))
    existing_username = result.scalars().first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already registered")
    result = await db.execute(select(UserModel).where(UserModel.email == user.email))
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check for family/group signup
    family_invitees = getattr(user, 'family_invitees', None)
    if family_invitees:
        # 1. Create the primary user (without family_group_id)
        db_user = UserModel(
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            email=user.email,
            password_hash=hash_password(user.password),
            is_primary=True,
            family_group_id=None
        )
        db.add(db_user)
        await db.commit()  # Persist user and assign id
        await db.refresh(db_user)

        # 2. Create the family group with owner_user_id set
        family_group = FamilyGroup(owner_user_id=db_user.id, created_at=datetime.now(timezone.utc))
        db.add(family_group)
        await db.flush()  # Get family_group.id
        family_group_id = family_group.id

        # 3. Update the user with the family_group_id
        db_user.family_group_id = family_group_id
        db.add(db_user)
        await db.flush()

        # 4. Create invitations for family members
        for invitee in family_invitees:
            token = secrets.token_urlsafe(32)
            invitation = Invitation(
                family_group_id=family_group_id,
                email=invitee["email"],
                first_name=invitee["first_name"],
                last_name=invitee["last_name"],
                role=invitee["role"],
                status="pending",
                token=token,
                sent_at=datetime.now(timezone.utc)
            )
            db.add(invitation)
        await db.commit()
        await db.refresh(db_user)
        jti = str(uuid.uuid4())
        device_info = request.headers.get("X-Device-Info")
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        session = UserSession(
            user_id=db_user.id,
            token_jti=jti,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            is_current=True
        )
        db.add(session)
        await db.commit()
        access_token = create_access_token({"sub": str(db_user.id), "username": db_user.username, "email": db_user.email}, user=db_user, jti=jti)
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        db_user = UserModel(
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            email=user.email,
            password_hash=hash_password(user.password),
            is_primary=True
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        jti = str(uuid.uuid4())
        device_info = request.headers.get("X-Device-Info")
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        session = UserSession(
            user_id=db_user.id,
            token_jti=jti,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            is_current=True
        )
        db.add(session)
        await db.commit()
        access_token = create_access_token({"sub": str(db_user.id), "username": db_user.username, "email": db_user.email}, user=db_user, jti=jti)
        return {"access_token": access_token, "token_type": "bearer"}

@router.post("/signin")
async def signin(auth: UserAuth, request: Request, db: AsyncSession = Depends(get_db)):
    # Allow login with either username or email
    result = await db.execute(
        select(UserModel).where(
            (UserModel.username == auth.login) | (UserModel.email == auth.login)
        )
    )
    user = result.scalars().first()
    
    if not user or not verify_password(auth.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # Check if 2FA is enabled
    result = await db.execute(
        select(TwoFactorAuth).where(
            and_(TwoFactorAuth.user_id == user.id, TwoFactorAuth.is_enabled == True)
        )
    )
    two_factor = result.scalars().first()
    
    # Check for trusted device token
    trusted_device_token = request.cookies.get("trusted_device_token")
    print(f"DEBUG: Signin - Trusted device token from cookies: {trusted_device_token}")
    trusted_device = None
    
    if trusted_device_token and two_factor:
        # Verify trusted device
        from app.services.trusted_device_service import trusted_device_service
        trusted_device = await trusted_device_service.verify_trusted_device(
            db=db,
            token=trusted_device_token,
            request=request,
            user_id=user.id
        )
        print(f"DEBUG: Signin - Trusted device verification result: {trusted_device is not None}")
    else:
        print(f"DEBUG: Signin - No trusted device token or 2FA not enabled")
    
    # If 2FA is enabled and no valid trusted device, require 2FA
    if two_factor and not trusted_device:
        # Generate a temporary token for 2FA verification
        temp_token = create_access_token(
            {"sub": str(user.id), "username": user.username, "email": user.email, "temp_2fa": True}, 
            user=user, 
            expires_delta=timedelta(minutes=5)
        )
        
        # Send verification code if SMS or email
        if two_factor.method == 'sms':
            # In production, send actual SMS
            verification_code = "123456"  # Demo code
            # TODO: Implement actual SMS sending
        elif two_factor.method == 'email':
            # In production, send actual email
            verification_code = "123456"  # Demo code
            # TODO: Implement actual email sending
        
        return {
            "requires_2fa": True,
            "method": two_factor.method,
            "temp_token": temp_token,
            "message": f"Please verify your {two_factor.method} authentication"
        }
    
    # No 2FA required or trusted device found, proceed with normal login
    jti = str(uuid.uuid4())
    device_info = request.headers.get("X-Device-Info")
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    session = UserSession(
        user_id=user.id,
        token_jti=jti,
        device_info=device_info,
        ip_address=ip_address,
        user_agent=user_agent,
        is_current=True,
        trusted_device_id=trusted_device.id if trusted_device else None
    )
    db.add(session)
    await db.commit()
    
    access_token = create_access_token({"sub": str(user.id), "username": user.username, "email": user.email}, user=user, jti=jti)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/verify-2fa")
async def verify_2fa_login(request: Request, db: AsyncSession = Depends(get_db)):
    """Verify 2FA code during login and complete the authentication process"""
    print("DEBUG: verify-2fa endpoint called")
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: Request URL: {request.url}")
    print(f"DEBUG: Request headers: {dict(request.headers)}")
    
    auth_header = request.headers.get("Authorization")
    print(f"DEBUG: Authorization header: {auth_header}")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    temp_token = auth_header.split(" ")[1]
    print(f"DEBUG: Temp token: {temp_token[:20]}...")
    
    try:
        payload = jwt.decode(temp_token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"DEBUG: JWT payload: {payload}")
        
        if not payload.get("temp_2fa"):
            raise HTTPException(status_code=401, detail="Invalid temporary token")
        
        user_id = int(payload.get("sub"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"DEBUG: JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get the verification code from request body
    try:
        # Try to get the raw body first
        body_bytes = await request.body()
        print(f"DEBUG: Raw request body bytes: {body_bytes}")
        
        # Try to parse as JSON
        body = await request.json()
        print(f"DEBUG: Parsed request body: {body}")
        
        verification_code = body.get("code")
        if not verification_code:
            print(f"DEBUG: No 'code' field found in body: {body}")
            raise HTTPException(status_code=400, detail="Verification code is required")
            
    except Exception as e:
        print(f"DEBUG: Error parsing request body: {e}")
        print(f"DEBUG: Content-Type: {request.headers.get('content-type')}")
        raise HTTPException(status_code=400, detail="Invalid request body")
    
    print(f"DEBUG: Verification code extracted: {verification_code}")
    
    # Get user and 2FA settings
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    print(f"DEBUG: Found user: {user.email}")
    
    two_factor_result = await db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user_id, TwoFactorAuth.is_enabled == True))
    two_factor = two_factor_result.scalars().first()
    if not two_factor:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")
    
    print(f"DEBUG: Found 2FA settings: method={two_factor.method}")
    
    # Verify the code
    is_valid = False
    
    if two_factor.method == 'authenticator':
        if not two_factor.secret_key:
            raise HTTPException(status_code=500, detail="No secret key found")
        
        print(f"DEBUG: Using authenticator method, secret key: {two_factor.secret_key[:10]}...")
        totp = pyotp.TOTP(two_factor.secret_key)
        is_valid = totp.verify(verification_code, valid_window=1)
        print(f"DEBUG: TOTP verification result: {is_valid}")
    
    elif two_factor.method in ['sms', 'email']:
        # Verify against database temp_code fields
        if not two_factor.temp_code or not two_factor.temp_code_expires_at:
            print(f"DEBUG: No temp code found for {two_factor.method}")
            is_valid = False
        else:
            # Check if code is expired
            from datetime import datetime
            current_time = datetime.utcnow()
            if current_time > two_factor.temp_code_expires_at:
                print(f"DEBUG: Code expired for {two_factor.method}")
                is_valid = False
            else:
                # Check if code matches
                is_valid = two_factor.temp_code == verification_code
                print(f"DEBUG: Code verification result for {two_factor.method}: {is_valid}")
            
            # Clear temp code after verification attempt
            two_factor.temp_code = None
            two_factor.temp_code_expires_at = None
            await db.commit()
    
    # Check if it's a backup code
    if not is_valid:
        import hashlib
        code_hash = hashlib.sha256(verification_code.encode()).hexdigest()
        from app.models.two_factor_auth import TwoFactorBackupCode
        backup_result = await db.execute(select(TwoFactorBackupCode).where(
            TwoFactorBackupCode.user_id == user_id,
            TwoFactorBackupCode.code_hash == code_hash,
            TwoFactorBackupCode.is_used == False
        ))
        backup_code = backup_result.scalars().first()
        
        if backup_code:
            is_valid = True
            backup_code.is_used = True
            backup_code.used_at = datetime.utcnow()
            await db.commit()
    
    if not is_valid:
        print(f"DEBUG: Verification failed, code was invalid")
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    print(f"DEBUG: Verification successful, creating session")
    
    # Check if user wants to remember this device
    remember_device = body.get("remember_device", False)
    print(f"DEBUG: Verify 2FA - Remember device: {remember_device}")
    trusted_device = None
    
    if remember_device:
        # Create trusted device
        from app.services.trusted_device_service import trusted_device_service
        trusted_device_data = trusted_device_service.create_trusted_device(
            user_id=user.id,
            request=request,
            remember_device=True,
            expiration_days=7
        )
        
        if trusted_device_data:
            trusted_device = await trusted_device_service.save_trusted_device(
                db, 
                trusted_device_data["trusted_device"]
            )
            print(f"DEBUG: Verify 2FA - Trusted device created: {trusted_device is not None}")
        else:
            print(f"DEBUG: Verify 2FA - Failed to create trusted device data")
    else:
        print(f"DEBUG: Verify 2FA - User did not choose to remember device")
    
    # 2FA verified, create session and return access token
    jti = str(uuid.uuid4())
    device_info = request.headers.get("X-Device-Info")
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    session = UserSession(
        user_id=user.id,
        token_jti=jti,
        device_info=device_info,
        ip_address=ip_address,
        user_agent=user_agent,
        is_current=True,
        trusted_device_id=trusted_device.id if trusted_device else None
    )
    db.add(session)
    await db.commit()
    
    access_token = create_access_token({"sub": str(user.id), "username": user.username, "email": user.email}, user=user, jti=jti)
    
    # Create response with trusted device token if created
    response_data = {"access_token": access_token, "token_type": "bearer"}
    
    if trusted_device:
        response_data["trusted_device_token"] = trusted_device_data["token"]
        response_data["trusted_device_expires"] = trusted_device.expires_at.isoformat()
    
    print(f"DEBUG: Created access token, returning response")
    
    # Create response with cookie if trusted device was created
    from fastapi.responses import JSONResponse
    response = JSONResponse(content=response_data)
    
    if trusted_device:
        # Set trusted device token as HTTP-only cookie
        print(f"DEBUG: Verify 2FA - Setting trusted device cookie")
        response.set_cookie(
            key="trusted_device_token",
            value=trusted_device_data["token"],
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
    else:
        print(f"DEBUG: Verify 2FA - No trusted device to set cookie for")
    
    return response

@router.post("/send-sms-code")
def send_sms_code(request: Request, db: Session = Depends(get_db)):
    """Send SMS verification code"""
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
    
    # Get user and 2FA settings
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    two_factor = db.query(TwoFactorAuth).filter(TwoFactorAuth.user_id == user_id, TwoFactorAuth.is_enabled == True).first()
    if not two_factor or two_factor.method != 'sms':
        raise HTTPException(status_code=400, detail="SMS 2FA is not enabled")
    
    if not two_factor.phone_number:
        raise HTTPException(status_code=400, detail="No phone number configured for SMS 2FA")
    
    # Send SMS using production service
    success = notification_service.send_2fa_sms(user_id, two_factor.phone_number)
    
    if success:
        return {"message": "SMS verification code sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send SMS verification code")

@router.post("/send-email-code")
def send_email_code(request: Request, db: Session = Depends(get_db)):
    """Send email verification code"""
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
    
    # Get user and 2FA settings
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    two_factor = db.query(TwoFactorAuth).filter(TwoFactorAuth.user_id == user_id, TwoFactorAuth.is_enabled == True).first()
    if not two_factor or two_factor.method != 'email':
        raise HTTPException(status_code=400, detail="Email 2FA is not enabled")
    
    # Send email using production service
    success = notification_service.send_2fa_email(user_id, user.email)
    
    if success:
        return {"message": "Email verification code sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email verification code")

# --- fastapi-users setup ---
async def get_user_db(db: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(db, UserModel)

class UserManager(BaseUserManager[UserModel, int]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)

# JWT strategy
cookie_transport = CookieTransport(cookie_name="auth", cookie_max_age=3600)
def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)  # type: ignore

jwt_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[UserModel, int](
    get_user_manager,
    [jwt_backend],
)

# --- Google OAuth2 setup ---
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set for Google OAuth2.")

oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

def get_redirect_uri(request: Request):
    # Use hardcoded redirect URI to avoid mismatches
    return "http://localhost:8000/auth/google/callback"

@router.get("/google/login")
async def auth_google_login(request: Request):
    redirect_uri = get_redirect_uri(request)
    print(f"DEBUG: Redirect URI being used: {redirect_uri}")
    print(f"DEBUG: Google OAuth client registered: {hasattr(oauth, 'google')}")
    print(f"DEBUG: OAuth object: {oauth}")
    print(f"DEBUG: OAuth registered clients: {oauth._clients}")
    
    if not hasattr(oauth, 'google') or oauth.google is None:
        raise HTTPException(status_code=500, detail="Google OAuth client not registered.")
    
    try:
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        print(f"DEBUG: Error in Google login: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Google OAuth redirect failed: {str(e)}")

@router.get("/google/callback")
async def auth_google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    # Debug database connection
    print(f"DEBUG: Database URL: {os.getenv('DB_URL')}")
    print(f"DEBUG: Database session: {db}")
    
    if not hasattr(oauth, 'google') or oauth.google is None:
        raise HTTPException(status_code=500, detail="Google OAuth client not registered.")
    
    try:
        # Debug: Print request parameters
        print(f"DEBUG: Request URL: {request.url}")
        print(f"DEBUG: Request query params: {request.query_params}")
        
        # Check if we have the authorization code
        code = request.query_params.get('code')
        if not code:
            error = request.query_params.get('error')
            error_description = request.query_params.get('error_description', '')
            raise HTTPException(
                status_code=400, 
                detail=f"Google OAuth error: {error} - {error_description}"
            )
        
        # Get token
        token = await oauth.google.authorize_access_token(request)
        print(f"DEBUG: Token received: {token}")
        
        # Get user info from Google's userinfo endpoint
        try:
            resp = await oauth.google.parse_id_token(request, token)
            print(f"DEBUG: User info from parse_id_token: {resp}")
            user_info = resp if isinstance(resp, dict) else {}
        except Exception as parse_error:
            print(f"DEBUG: parse_id_token failed: {parse_error}")
            # Fallback: try to get user info from token directly
            user_info = token.get('userinfo', {})
            if not user_info:
                # Try to get user info from the token response
                user_info = {
                    'sub': token.get('sub'),
                    'email': token.get('email'),
                    'name': token.get('name', ''),
                    'given_name': token.get('given_name', ''),
                    'family_name': token.get('family_name', '')
                }
        
        # Extract user information from the response
        google_id = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name', '')
        given_name = user_info.get('given_name', '')
        family_name = user_info.get('family_name', '')
        
        print(f"DEBUG: Extracted user info - email: {email}, name: {name}")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        # Check if user exists
        result = await db.execute(select(UserModel).where(UserModel.email == email))
        user = result.scalars().first()
        
        if user:
            # User exists, log them in
            print(f"DEBUG: Existing user found: {user.email}")
            # Update avatar and names if missing or outdated
            updated = False
            if hasattr(user, 'avatar_url') and user_info.get('picture') and user.avatar_url != user_info.get('picture'):
                user.avatar_url = user_info.get('picture')
                updated = True
            if hasattr(user, 'first_name') and given_name and user.first_name != given_name:
                user.first_name = given_name
                updated = True
            if hasattr(user, 'last_name') and family_name and user.last_name != family_name:
                user.last_name = family_name
                updated = True
            if updated:
                db.add(user)
                await db.commit()
                await db.refresh(user)
            
            # Check if 2FA is enabled
            two_factor_result = await db.execute(select(TwoFactorAuth).where(TwoFactorAuth.user_id == user.id, TwoFactorAuth.is_enabled == True))
            two_factor = two_factor_result.scalars().first()
            
            # Check for trusted device token
            trusted_device_token = request.cookies.get("trusted_device_token")
            trusted_device = None
            
            if trusted_device_token and two_factor:
                # Verify trusted device
                from app.services.trusted_device_service import trusted_device_service
                trusted_device = await trusted_device_service.verify_trusted_device(
                    db=db,
                    token=trusted_device_token,
                    request=request,
                    user_id=user.id
                )
                print(f"DEBUG: Google OAuth - Trusted device verification result: {trusted_device is not None}")
            
            if two_factor and not trusted_device:
                # Generate a temporary token for 2FA verification
                temp_token = create_access_token(
                    {"sub": str(user.id), "username": user.username, "email": user.email, "temp_2fa": True}, 
                    user=user, 
                    expires_delta=timedelta(minutes=5)
                )
                
                # Redirect to 2FA verification page
                redirect_url = f"http://localhost:4200/two-factor-verification?temp_token={temp_token}&method={two_factor.method}"
                return RedirectResponse(url=redirect_url)
            
            # No 2FA required, proceed with normal login
            jti = str(uuid.uuid4())
            device_info = request.headers.get("X-Device-Info")
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            session = UserSession(
                user_id=user.id,
                token_jti=jti,
                device_info=device_info,
                ip_address=ip_address,
                user_agent=user_agent,
                is_current=True,
                trusted_device_id=trusted_device.id if trusted_device else None
            )
            db.add(session)
            await db.commit()
            access_token = create_access_token({"sub": str(user.id), "username": user.username, "email": user.email}, user=user, jti=jti)
            # Redirect to frontend with token
            redirect_url = f"http://localhost:4200/dashboard?token={access_token}"
            return RedirectResponse(url=redirect_url)
        else:
            # Create new user
            print(f"DEBUG: Creating new user for email: {email}")
            
            # Generate username from email
            username = email.split('@')[0]
            base_username = username
            counter = 1
            
            # Ensure unique username
            while True:
                result = await db.execute(select(UserModel).where(UserModel.username == username))
                existing_user = result.scalars().first()
                if not existing_user:
                    break
                username = f"{base_username}{counter}"
                counter += 1
            
            # Create user
            db_user = UserModel(
                first_name=given_name or (name.split()[0] if name else ''),
                last_name=family_name or (' '.join(name.split()[1:]) if name and len(name.split()) > 1 else ''),
                username=username,
                email=email,
                password_hash="",  # No password for OAuth users
                is_primary=True,
                auth_provider='google',  # Set auth provider to google
                provider_id=google_id,  # Set provider ID to Google user ID
                is_verified=True,  # Google users are automatically verified
                avatar_url=user_info.get('picture')  # Save Google avatar
            )
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
            
            jti = str(uuid.uuid4())
            device_info = request.headers.get("X-Device-Info")
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            session = UserSession(
                user_id=db_user.id,
                token_jti=jti,
                device_info=device_info,
                ip_address=ip_address,
                user_agent=user_agent,
                is_current=True
            )
            db.add(session)
            await db.commit()
            access_token = create_access_token({"sub": str(db_user.id), "username": db_user.username, "email": db_user.email}, user=db_user, jti=jti)
            # Redirect to frontend with token
            redirect_url = f"http://localhost:4200/dashboard?token={access_token}"
            return RedirectResponse(url=redirect_url)
            
    except Exception as e:
        print(f"DEBUG: Error in Google callback: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Google OAuth callback failed: {str(e)}")

@router.get("/me")
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """Get current user information"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Decode token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
            user_id = int(payload.get("sub"))
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # In all auth-required endpoints, add logic to check token_version in JWT matches DB (pseudo):
        # if payload['token_version'] != user.token_version: raise HTTPException(status_code=401, detail='Session expired, please sign in again.')

        # Return user data
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_primary": user.is_primary,
            "family_group_id": user.family_group_id,
            "created_at": user.created_at,
            "authProvider": getattr(user, 'auth_provider', 'local'),
            "providerId": getattr(user, 'provider_id', None),
            "avatarUrl": getattr(user, 'avatar_url', None)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_current_user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/setup-family")
async def setup_family(
    request: Request, 
    setup_data: FamilyGroupSetupRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Setup family group and send invitations"""
    try:
        # Get current user from token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Decode token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
            user_id = int(payload.get("sub"))
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get current user
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        current_user = result.scalars().first()
        
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user already has a family group
        if current_user.family_group_id is not None:
            raise HTTPException(status_code=400, detail="User already belongs to a family group")
        
        # Create family group
        family_group = FamilyGroup(
            owner_user_id=current_user.id,
            family_name=setup_data.family_name,
            created_at=datetime.now(timezone.utc)
        )
        db.add(family_group)
        await db.flush()  # Get family_group.id
        
        # Update current user with family_group_id
        setattr(current_user, 'family_group_id', family_group.id)
        setattr(current_user, 'is_primary', True)
        db.add(current_user)
        
        # Create invitations for family members
        for invitee in setup_data.invitees:
            token = secrets.token_urlsafe(32)
            invitation = Invitation(
                family_group_id=family_group.id,
                email=invitee.email,
                first_name=invitee.first_name,
                last_name=invitee.last_name,
                role=invitee.role,
                status="pending",
                token=token,
                sent_at=datetime.now(timezone.utc)
            )
            db.add(invitation)
            
            # Send invitation email
            background_tasks.add_task(
                send_invitation_email,
                invitee.email,
                invitee.first_name,
                token
            )
        
        await db.commit()
        
        return {
            "message": "Family group created successfully",
            "family_group_id": family_group.id,
            "invitations_sent": len(setup_data.invitees)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in setup_family: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/preferences")
async def save_user_preferences(
    request: Request,
    preferences: UserPreferences,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """Save user preferences"""
    try:
        # Get current user from token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Decode token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
            user_id = int(payload.get("sub"))
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get current user
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user preferences exist
        result = await db.execute(
            select(UserPreferencesModel).where(UserPreferencesModel.user_id == user_id)
        )
        user_prefs = result.scalars().first()
        
        if user_prefs:
            # Update existing preferences
            setattr(user_prefs, 'account_type', preferences.account_type)
            setattr(user_prefs, 'primary_goal', preferences.primary_goal)
            setattr(user_prefs, 'financial_focus', preferences.financial_focus)
            setattr(user_prefs, 'experience_level', preferences.experience_level)
            setattr(user_prefs, 'updated_at', datetime.now(timezone.utc))
        else:
            # Create new preferences
            user_prefs = UserPreferencesModel(
                user_id=user_id,
                account_type=preferences.account_type,
                primary_goal=preferences.primary_goal,
                financial_focus=preferences.financial_focus,
                experience_level=preferences.experience_level,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(user_prefs)
        
        await db.commit()
        
        # Invalidate cache
        cache_key = f"user_preferences:{user_id}"
        await cache.delete(cache_key)
        
        return {"message": "Preferences saved successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in save_user_preferences: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/preferences")
async def get_user_preferences(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """Get user preferences"""
    try:
        # Get current user from token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Decode token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
            user_id = int(payload.get("sub"))
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Try to get from cache first
        cache_key = f"user_preferences:{user_id}"
        cached_prefs = await cache.get(cache_key)
        if cached_prefs:
            return cached_prefs
        
        # Get from database
        result = await db.execute(
            select(UserPreferencesModel).where(UserPreferencesModel.user_id == user_id)
        )
        user_prefs = result.scalars().first()
        
        if not user_prefs:
            return {"has_preferences": False}
        
        preferences_data = {
            "has_preferences": True,
            "account_type": user_prefs.account_type,
            "primary_goal": user_prefs.primary_goal,
            "financial_focus": user_prefs.financial_focus,
            "experience_level": user_prefs.experience_level,
            "created_at": user_prefs.created_at,
            "updated_at": user_prefs.updated_at
        }
        
        # Cache for 30 minutes
        await cache.set(cache_key, preferences_data, expire=1800)
        
        return preferences_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_user_preferences: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 