from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.models.user_session import UserSession
from app.schemas.user_session import UserSessionResponse
from app.models.user import User
import jwt
import os
from datetime import datetime
from typing import List

router = APIRouter(prefix="/users/sessions", tags=["sessions"])

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"

def get_user_and_jti(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        user_id = int(payload.get("sub"))
        jti = payload.get("jti")
        if not user_id or not jti:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id, jti
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/", response_model=List[UserSessionResponse])
async def list_sessions(request: Request, db: AsyncSession = Depends(get_db)):
    user_id, jti = get_user_and_jti(request)
    # Refresh last_active_at for current session
    result = await db.execute(select(UserSession).where(UserSession.user_id == user_id, UserSession.token_jti == jti))
    current_session = result.scalars().first()
    if current_session:
        setattr(current_session, 'last_active_at', datetime.utcnow())
        await db.commit()
    result = await db.execute(select(UserSession).where(UserSession.user_id == user_id))
    return result.scalars().all()

@router.delete("/{session_id}")
async def revoke_session(session_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user_id, jti = get_user_and_jti(request)
    result = await db.execute(select(UserSession).where(UserSession.id == session_id, UserSession.user_id == user_id))
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()
    return {"message": "Session revoked"}

@router.delete("/")
async def revoke_all_sessions(request: Request, db: AsyncSession = Depends(get_db)):
    user_id, jti = get_user_and_jti(request)
    # Keep current session (by jti), delete all others
    result = await db.execute(select(UserSession).where(UserSession.user_id == user_id))
    sessions = result.scalars().all()
    for session in sessions:
        if session.token_jti != jti:
            await db.delete(session)
    await db.commit()
    return {"message": "All other sessions revoked"} 