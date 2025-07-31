from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.models.user import User as UserModel
from app.models.family_group import FamilyGroup
from app.models.invitation import Invitation
from typing import List, cast
from passlib.context import CryptContext
from datetime import datetime, timezone
import secrets
from app.services.logging_service import logging_service

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