from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # type: ignore
    return encoded_jwt

def create_reset_token(user_id: int, email: str):
    expire = timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    return create_access_token({"sub": str(user_id), "email": email, "reset": True}, expire)

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

class ForgotPasswordRequest(BaseModel):
    email: str

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
async def reset_password(token: str, new_password: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        if not payload.get("reset"):
            raise HTTPException(status_code=400, detail="Invalid token.")
        user_id = int(payload.get("sub"))
        email = payload.get("email")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Reset token expired.")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid token.")
    result = await db.execute(select(UserModel).where(UserModel.id == user_id, UserModel.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token.")
    user.password_hash = hash_password(new_password)  # type: ignore
    await db.commit()
    return {"message": "Password reset successful."}

@router.post("/signup")
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
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
        access_token = create_access_token({"sub": str(db_user.id), "username": db_user.username, "email": db_user.email})
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
        access_token = create_access_token({"sub": str(db_user.id), "username": db_user.username, "email": db_user.email})
        return {"access_token": access_token, "token_type": "bearer"}

@router.post("/signin")
def signin(auth: UserAuth, db: Session = Depends(get_db)):
    # Allow login with either username or email
    user = db.query(UserModel).filter((UserModel.username == auth.login) | (UserModel.email == auth.login)).first()
    if not user or not verify_password(auth.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token({"sub": str(user.id), "username": user.username, "email": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

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
        
        print(f"DEBUG: Authorization code received: {code[:10]}...")
        
        token = await oauth.google.authorize_access_token(request)
        print(f"DEBUG: Token received: {token}")
        
        # Get user info from the userinfo endpoint with the token
        user_info = await oauth.google.userinfo(token=token)
        print(f"DEBUG: User info received: {user_info}")
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Google login failed - no user info")
        
        # Extract user information
        email = user_info.get("email")
        sub = user_info.get("sub")
        given_name = user_info.get("given_name", "")
        family_name = user_info.get("family_name", "")
        
        if not email or not sub:
            raise HTTPException(status_code=400, detail="Google login failed - missing email or sub")
        
        # Test database connection first
        try:
            test_result = await db.execute(select(UserModel).limit(1))
            print(f"DEBUG: Database connection test successful")
        except Exception as db_error:
            print(f"DEBUG: Database connection error: {db_error}")
            raise HTTPException(status_code=500, detail=f"Database connection failed: {str(db_error)}")
        
        # Find or create user
        result = await db.execute(select(UserModel).where(UserModel.provider_id == sub, UserModel.auth_provider == "google"))
        user = result.scalars().first()
        
        if not user:
            # Check if email already exists for local user
            result = await db.execute(select(UserModel).where(UserModel.email == email))
            existing = result.scalars().first()
            if existing:
                raise HTTPException(status_code=400, detail="Email already registered with local account")
            
            user = UserModel(
                first_name=given_name,
                last_name=family_name,
                username=email,
                email=email,
                password_hash="",
                is_primary=True,
                auth_provider="google",
                provider_id=sub,
                is_active=True,
                is_superuser=False,
                is_verified=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        # Issue JWT
        access_token = create_access_token({"sub": str(user.id), "username": user.username, "email": user.email})
        
        # Check if this is a new user (no family_group_id set)
        is_new_user = user.family_group_id is None
        
        # Redirect to frontend with token and new_user flag
        response = Response(status_code=302)
        response.headers["Location"] = f"http://localhost:4200/social-login?token={access_token}&new_user={str(is_new_user).lower()}"
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error in Google callback: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Google login failed: {str(e)}")

@router.get("/me")
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """Get current user information from JWT token"""
    try:
        # Get the Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        user_id = int(payload.get("sub"))
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Return user information (excluding sensitive data)
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_primary": user.is_primary,
            "family_group_id": user.family_group_id,
            "auth_provider": getattr(user, 'auth_provider', None)
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"Error in /me endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/setup-family")
async def setup_family(
    request: Request, 
    setup_data: FamilyGroupSetupRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Setup family group for Google OAuth users"""
    try:
        # Get the Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        user_id = int(payload.get("sub"))
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Check if user already has a family group
        if user.family_group_id is not None:
            raise HTTPException(status_code=400, detail="User already has a family group")
        
        # Create family group (now with family_name)
        family_group = FamilyGroup(
            owner_user_id=user.id, 
            family_name=setup_data.family_name,
            created_at=datetime.now(timezone.utc)
        )
        db.add(family_group)
        await db.flush()  # Get family_group.id
        
        # Update user with family_group_id
        user.family_group_id = family_group.id
        db.add(user)
        await db.flush()
        
        # Create invitations for family members
        invitations = []
        for member_data in setup_data.invitees:
            token = secrets.token_urlsafe(32)
            invitation = Invitation(
                family_group_id=family_group.id,
                email=member_data.email,
                first_name=member_data.first_name,
                last_name=member_data.last_name,
                role=member_data.role,
                status="pending",
                token=token,
                sent_at=datetime.now(timezone.utc)
            )
            db.add(invitation)
            invitations.append((member_data.email, member_data.first_name, token))
        
        await db.commit()
        
        # Send invitation emails in the background
        print(f"Scheduling {len(invitations)} invitation emails to be sent...")
        for email, first_name, token in invitations:
            background_tasks.add_task(send_invitation_email, email, first_name, token)
            print(f"Scheduled invitation email for {email}")
        
        return {
            "message": "Family group created successfully",
            "family_group_id": family_group.id,
            "family_name": family_group.family_name,
            "invitations_sent": len(setup_data.invitees)
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"Error in setup-family endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/preferences")
async def save_user_preferences(
    request: Request,
    preferences: UserPreferences,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """Save user preferences from questionnaire"""
    try:
        # Get the Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        user_id = int(payload.get("sub"))
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Check if user already has preferences
        result = await db.execute(select(UserPreferencesModel).where(UserPreferencesModel.user_id == user.id))
        existing_preferences = result.scalars().first()
        
        if existing_preferences:
            # Update existing preferences
            existing_preferences.account_type = preferences.account_type  # type: ignore
            existing_preferences.primary_goal = preferences.primary_goal  # type: ignore
            existing_preferences.financial_focus = preferences.financial_focus  # type: ignore
            existing_preferences.experience_level = preferences.experience_level  # type: ignore
            # No need to add existing object back to session
        else:
            # Create new preferences
            user_preferences = UserPreferencesModel(
                user_id=user.id,
                account_type=preferences.account_type,
                primary_goal=preferences.primary_goal,
                financial_focus=preferences.financial_focus,
                experience_level=preferences.experience_level
            )
            db.add(user_preferences)
        
        await db.commit()
        
        # Invalidate cache for this user's preferences
        cache_key = CacheKeys.user_preferences(cast(int, user.id))
        await cache.delete(cache_key)
        
        return {
            "message": "Preferences saved successfully",
            "preferences": preferences.dict()
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"Error in save preferences endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/preferences")
async def get_user_preferences(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_cache)
):
    """Get user preferences from questionnaire"""
    try:
        # Get the Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        user_id = int(payload.get("sub"))
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Try to get from cache first
        cache_key = CacheKeys.user_preferences(cast(int, user.id))
        cached_preferences = await cache.get(cache_key)
        
        if cached_preferences is not None:
            return cached_preferences
        
        # Get user preferences from database
        result = await db.execute(select(UserPreferencesModel).where(UserPreferencesModel.user_id == user.id))
        user_preferences = result.scalars().first()
        
        if not user_preferences:
            response = {"has_preferences": False}
            # Cache the result for 5 minutes
            await cache.set(cache_key, response, expire=300)
            return response
        
        response = {
            "has_preferences": True,
            "preferences": {
                "account_type": user_preferences.account_type,
                "primary_goal": user_preferences.primary_goal,
                "financial_focus": user_preferences.financial_focus,
                "experience_level": user_preferences.experience_level
            }
        }
        
        # Cache the result for 1 hour
        await cache.set(cache_key, response, expire=3600)
        return response
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"Error in get preferences endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 