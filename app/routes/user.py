from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, NotificationSettings, NotificationSettingsCreate, NotificationSettingsUpdate, PrivacySettings, PrivacySettingsCreate, PrivacySettingsUpdate, AccountType
from app.models.user import User as UserModel
from app.models.family_group import FamilyGroup
from app.models.invitation import Invitation
from app.models.notification_settings import NotificationSettings as NotificationSettingsModel
from app.models.privacy_settings import PrivacySettings as PrivacySettingsModel
from typing import List, cast
from passlib.context import CryptContext
from datetime import datetime, timezone
import secrets
from app.services.logging_service import logging_service
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/users", tags=["users"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_family_invitations(family_group_id: int, invitees: List[dict], db: Session):
    """Create invitation records for family members"""
    invitations = []
    for invitee in invitees:
        token = secrets.token_urlsafe(12)
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
        invitations.append(invitation)
    return invitations

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_username = db.query(UserModel).filter(UserModel.username == user.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already registered")
    existing_email = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check for family/group signup
    family_invitees = getattr(user, 'family_invitees', None)
    
    if family_invitees:
        # 1. Create the primary user (without family_group_id)
        db_user = UserModel(
            first_name=user.first_name,  # type: ignore
            last_name=user.last_name,  # type: ignore
            username=user.username,  # type: ignore
            email=user.email,  # type: ignore
            password_hash=hash_password(user.password),  # type: ignore
            is_primary=True,
            family_group_id=None
        )
        db.add(db_user)
        db.commit()  # Persist user and assign id
        db.refresh(db_user)

        # 2. Create the family group with owner_user_id set
        family_group = FamilyGroup(owner_user_id=db_user.id, created_at=datetime.now(timezone.utc))
        db.add(family_group)
        db.flush()  # Get family_group.id
        family_group_id = cast(int, family_group.id)

        # 3. Update the user with the family_group_id
        db_user.family_group_id = family_group_id  # type: ignore
        db.add(db_user)
        db.flush()

        # Now create invitations for family members
        create_family_invitations(family_group_id, family_invitees, db)
    else:
        # Individual signup - just create the user
        db_user = UserModel(
            first_name=user.first_name,  # type: ignore
            last_name=user.last_name,  # type: ignore
            username=user.username,  # type: ignore
            email=user.email,  # type: ignore
            password_hash=hash_password(user.password),  # type: ignore
            is_primary=True
        )
        db.add(db_user)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(UserModel).offset(skip).limit(limit).all()
    return users

# Notification Settings
@router.get("/notification-settings", response_model=NotificationSettings)
async def get_notification_settings(current_user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    # Get existing settings or create default ones
    result = await db.execute(select(NotificationSettingsModel).where(NotificationSettingsModel.user_id == current_user_id))
    settings = result.scalars().first()
    
    if not settings:
        # Create default settings
        settings = NotificationSettingsModel(
            user_id=current_user_id,
            email_notifications=True,
            push_notifications=True,
            transaction_alerts=True,
            budget_alerts=True,
            family_updates=True,
            marketing_emails=False
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    # Convert to response format
    return NotificationSettings(
        emailNotifications=settings.email_notifications,
        pushNotifications=settings.push_notifications,
        transactionAlerts=settings.transaction_alerts,
        budgetAlerts=settings.budget_alerts,
        familyUpdates=settings.family_updates,
        marketingEmails=settings.marketing_emails
    )

@router.put("/notification-settings", response_model=NotificationSettings)
async def update_notification_settings(settings_update: NotificationSettingsUpdate, current_user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    # Get existing settings or create new ones
    result = await db.execute(select(NotificationSettingsModel).where(NotificationSettingsModel.user_id == current_user_id))
    settings = result.scalars().first()
    
    if not settings:
        # Create new settings with defaults
        settings = NotificationSettingsModel(user_id=current_user_id)
        db.add(settings)
    
    # Update only the fields that were provided
    if settings_update.emailNotifications is not None:
        settings.email_notifications = settings_update.emailNotifications
    if settings_update.pushNotifications is not None:
        settings.push_notifications = settings_update.pushNotifications
    if settings_update.transactionAlerts is not None:
        settings.transaction_alerts = settings_update.transactionAlerts
    if settings_update.budgetAlerts is not None:
        settings.budget_alerts = settings_update.budgetAlerts
    if settings_update.familyUpdates is not None:
        settings.family_updates = settings_update.familyUpdates
    if settings_update.marketingEmails is not None:
        settings.marketing_emails = settings_update.marketingEmails
    
    await db.commit()
    await db.refresh(settings)
    
    # Log the update
    await logging_service.log_audit_event(
        event_type="UPDATE",
        resource_type="notification_settings",
        action="update",
        resource_id=settings.id,
        user_id=current_user_id,
        changes={
            "email_notifications": settings.email_notifications,
            "push_notifications": settings.push_notifications,
            "transaction_alerts": settings.transaction_alerts,
            "budget_alerts": settings.budget_alerts,
            "family_updates": settings.family_updates,
            "marketing_emails": settings.marketing_emails
        }
    )
    
    # Return the updated settings
    return NotificationSettings(
        emailNotifications=settings.email_notifications,
        pushNotifications=settings.push_notifications,
        transactionAlerts=settings.transaction_alerts,
        budgetAlerts=settings.budget_alerts,
        familyUpdates=settings.family_updates,
        marketingEmails=settings.marketing_emails
    )

# Privacy Settings
@router.get("/privacy-settings", response_model=PrivacySettings)
async def get_privacy_settings(current_user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    # Get existing settings or create default ones
    result = await db.execute(select(PrivacySettingsModel).where(PrivacySettingsModel.user_id == current_user_id))
    settings = result.scalars().first()
    
    if not settings:
        # Create default settings
        settings = PrivacySettingsModel(
            user_id=current_user_id,
            profile_visibility="private",
            data_sharing=False,
            analytics_sharing=True,
            allow_family_access=True
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    # Convert to response format
    return PrivacySettings(
        profileVisibility=settings.profile_visibility,
        dataSharing=settings.data_sharing,
        analyticsSharing=settings.analytics_sharing,
        allowFamilyAccess=settings.allow_family_access
    )

@router.put("/privacy-settings", response_model=PrivacySettings)
async def update_privacy_settings(settings_update: PrivacySettingsUpdate, current_user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    # Get existing settings or create new ones
    result = await db.execute(select(PrivacySettingsModel).where(PrivacySettingsModel.user_id == current_user_id))
    settings = result.scalars().first()
    
    if not settings:
        # Create new settings with defaults
        settings = PrivacySettingsModel(user_id=current_user_id)
        db.add(settings)
    
    # Update only the fields that were provided
    if settings_update.profileVisibility is not None:
        settings.profile_visibility = settings_update.profileVisibility
    if settings_update.dataSharing is not None:
        settings.data_sharing = settings_update.dataSharing
    if settings_update.analyticsSharing is not None:
        settings.analytics_sharing = settings_update.analyticsSharing
    if settings_update.allowFamilyAccess is not None:
        settings.allow_family_access = settings_update.allowFamilyAccess
    
    await db.commit()
    await db.refresh(settings)
    
    # Log the update
    await logging_service.log_audit_event(
        event_type="UPDATE",
        resource_type="privacy_settings",
        action="update",
        resource_id=settings.id,
        user_id=current_user_id,
        changes={
            "profile_visibility": settings.profile_visibility,
            "data_sharing": settings.data_sharing,
            "analytics_sharing": settings.analytics_sharing,
            "allow_family_access": settings.allow_family_access
        }
    )
    
    # Return the updated settings
    return PrivacySettings(
        profileVisibility=settings.profile_visibility,
        dataSharing=settings.data_sharing,
        analyticsSharing=settings.analytics_sharing,
        allowFamilyAccess=settings.allow_family_access
    )

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.first_name is not None:
        db_user.first_name = user.first_name  # type: ignore
    if user.last_name is not None:
        db_user.last_name = user.last_name  # type: ignore
    if user.username is not None:
        existing = db.query(UserModel).filter(UserModel.username == user.username, UserModel.id != user_id).first()
        if existing:
            # Audit log for failed username update
            import asyncio
            asyncio.create_task(logging_service.log_failed_audit_event(
                event_type="UPDATE",
                resource_type="USER",
                action="Attempted username update",
                user_id=user_id,
                failure_reason="Username already registered",
                meta={"attempted_username": user.username}
            ))
            raise HTTPException(status_code=400, detail="Username already registered")
        db_user.username = user.username  # type: ignore
    if user.email is not None:
        existing = db.query(UserModel).filter(UserModel.email == user.email, UserModel.id != user_id).first()
        if existing:
            # Audit log for failed email update
            import asyncio
            asyncio.create_task(logging_service.log_failed_audit_event(
                event_type="UPDATE",
                resource_type="USER",
                action="Attempted email update",
                user_id=user_id,
                failure_reason="Email already registered",
                meta={"attempted_email": user.email}
            ))
            raise HTTPException(status_code=400, detail="Email already registered")
        db_user.email = user.email  # type: ignore
    if user.password is not None:
        db_user.password_hash = hash_password(user.password)  # type: ignore
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return None

# Account Type
@router.get("/account-type", response_model=AccountType)
def get_account_type(current_user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    # For now, return personal account type. In a real app, you'd check the user's family_group_id
    return AccountType(type="personal")

# Convert to Family Account
@router.post("/convert-to-family", response_model=AccountType)
def convert_to_family_account(current_user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    # For now, just return family account type. In a real app, you'd:
    # 1. Create a FamilyGroup
    # 2. Update the user's family_group_id
    # 3. Set the user as the owner
    return AccountType(type="family", familyGroupId=1) 