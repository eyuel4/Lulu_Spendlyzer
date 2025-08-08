from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.invitation import Invitation
from app.models.user import User as UserModel
from app.schemas.invitation import InvitationRead
from app.schemas.user import UserRead
from app.models.family_group import FamilyGroup
from app.core.auth import hash_password, get_current_user_id  # type: ignore
from datetime import datetime, timezone, timedelta
import secrets
from typing import List

router = APIRouter(prefix="/family", tags=["family"])

@router.post("/invite", response_model=list[InvitationRead])
async def invite(invite_data: dict, db: AsyncSession = Depends(get_db)):
    family_group_id = invite_data["family_group_id"]
    invitees = invite_data["invitees"]
    invitations = []
    for invitee in invitees:
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
        invitations.append(invitation)
    await db.commit()
    return invitations

@router.get("/invite/accept/{token}")
async def accept_invite(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invitation).where(Invitation.token == token))
    invitation = result.scalars().first()
    
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    if getattr(invitation, 'status', None) != "pending":
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    sent_at = getattr(invitation, 'sent_at', None)
    if sent_at is None:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    
    # Ensure sent_at is timezone-aware for comparison
    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=timezone.utc)
    
    if sent_at < datetime.now(timezone.utc) - timedelta(days=5):
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    
    # Get inviter's name if possible
    result = await db.execute(select(FamilyGroup).where(FamilyGroup.id == invitation.family_group_id))
    family_group = result.scalars().first()
    inviter = None
    if family_group is not None and getattr(family_group, 'owner_user_id', None) not in (None,):
        result = await db.execute(select(UserModel).where(UserModel.id == family_group.owner_user_id))
        inviter_user = result.scalars().first()
        if inviter_user is not None:
            inviter = f"{inviter_user.first_name} {inviter_user.last_name}"
    
    return {
        "first_name": invitation.first_name,
        "last_name": invitation.last_name,
        "email": invitation.email,
        "role": invitation.role,
        "inviter": inviter
    }

@router.post("/register-invitee", response_model=UserRead)
async def register_invitee(data: dict, db: AsyncSession = Depends(get_db)):
    token = data["token"]
    username = data["username"]
    password = data["password"]
    
    result = await db.execute(select(Invitation).where(Invitation.token == token))
    invitation = result.scalars().first()
    
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    if getattr(invitation, 'status', None) != "pending":
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    sent_at = getattr(invitation, 'sent_at', None)
    if sent_at is None:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    
    # Ensure sent_at is timezone-aware for comparison
    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=timezone.utc)
    
    if sent_at < datetime.now(timezone.utc) - timedelta(days=5):
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    
    # Check for username uniqueness
    result = await db.execute(select(UserModel).where(UserModel.username == username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    db_user = UserModel(
        first_name=invitation.first_name,
        last_name=invitation.last_name,
        username=username,
        email=invitation.email,
        password_hash=hash_password(password),
        is_primary=False,
        family_group_id=invitation.family_group_id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(db_user)
    invitation.status = "accepted"  # type: ignore
    await db.commit()
    await db.refresh(db_user)
    return db_user

# Family Members
@router.get("/members", response_model=List[dict])
async def get_family_members(current_user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    # For now, return empty list. In a real app, you'd query family members based on family_group_id
    return []

# Family Invitations
@router.get("/invitations", response_model=List[dict])
async def get_family_invitations(current_user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    # For now, return empty list. In a real app, you'd query invitations based on family_group_id
    return []

@router.post("/invitations")
async def send_family_invitation(invitation_data: dict, current_user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    # For now, just return success. In a real app, you'd create an invitation record
    return {"message": "Invitation sent successfully"}

@router.post("/invitations/{invitation_id}/resend")
async def resend_family_invitation(invitation_id: int, current_user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    # For now, just return success. In a real app, you'd resend the invitation
    return {"message": "Invitation resent successfully"}

@router.delete("/invitations/{invitation_id}")
async def cancel_family_invitation(invitation_id: int, current_user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    # For now, just return success. In a real app, you'd cancel the invitation
    return {"message": "Invitation cancelled successfully"} 