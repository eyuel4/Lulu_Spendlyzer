from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.feature_request import FeatureRequest
from app.schemas.feature_request import FeatureRequestCreate, FeatureRequestResponse
from app.models.user import User
from typing import List
import jwt
import os
from datetime import datetime

router = APIRouter(prefix="/feature-requests", tags=["feature-requests"])

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"

def get_user_id_from_request(request: Request) -> int | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        return int(payload.get("sub"))
    except Exception:
        return None

@router.post("/", response_model=FeatureRequestResponse)
async def create_feature_request(
    data: FeatureRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_request(request)
    new_req = FeatureRequest(
        user_id=user_id,
        description=data.description,
        status="pending",
        created_at=datetime.utcnow()
    )
    db.add(new_req)
    await db.commit()
    await db.refresh(new_req)
    return new_req

@router.get("/", response_model=List[FeatureRequestResponse])
async def list_feature_requests(db: AsyncSession = Depends(get_db)):
    # For admin use only; no auth here for simplicity
    result = await db.execute(select(FeatureRequest).order_by(FeatureRequest.created_at.desc()))
    return result.scalars().all() 