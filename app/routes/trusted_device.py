from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.services.trusted_device_service import trusted_device_service
from app.schemas.trusted_device import (
    TrustedDeviceCreate, 
    TrustedDeviceResponse, 
    TrustedDeviceList,
    TrustedDeviceVerify,
    TrustedDeviceRevoke
)
from typing import List
import json

router = APIRouter(prefix="/auth", tags=["trusted-devices"])

@router.post("/trust-device", response_model=TrustedDeviceResponse)
async def create_trusted_device(
    request: Request,
    device_data: TrustedDeviceCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new trusted device for the current user"""
    try:
        # Create trusted device
        trusted_device_data = trusted_device_service.create_trusted_device(
            user_id=current_user_id,
            request=request,
            remember_device=device_data.remember_device,
            expiration_days=device_data.expiration_days
        )
        
        if not trusted_device_data:
            raise HTTPException(
                status_code=400, 
                detail="Failed to create trusted device"
            )
        
        # Save to database
        trusted_device = await trusted_device_service.save_trusted_device(
            db, 
            trusted_device_data["trusted_device"]
        )
        
        # Set secure HTTP-only cookie
        response = Response(content=json.dumps({
            "id": trusted_device.id,
            "device_name": trusted_device.device_name,
            "location": trusted_device.location,
            "expires_at": trusted_device.expires_at.isoformat(),
            "message": "Device trusted successfully"
        }))
        
        response.set_cookie(
            key="trusted_device_token",
            value=trusted_device_data["token"],
            max_age=device_data.expiration_days * 24 * 60 * 60,  # Convert days to seconds
            httponly=True,
            secure=True,  # Set to False in development
            samesite="strict"
        )
        
        return trusted_device
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create trusted device: {str(e)}"
        )

@router.post("/verify-trusted-device")
async def verify_trusted_device(
    request: Request,
    verify_data: TrustedDeviceVerify,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Verify a trusted device token"""
    try:
        trusted_device = await trusted_device_service.verify_trusted_device(
            db=db,
            token=verify_data.token,
            request=request,
            user_id=current_user_id
        )
        
        if not trusted_device:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired trusted device token"
            )
        
        return {
            "valid": True,
            "device_name": trusted_device.device_name,
            "location": trusted_device.location,
            "last_used": trusted_device.last_used_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify trusted device: {str(e)}"
        )

@router.get("/trusted-devices", response_model=TrustedDeviceList)
async def get_trusted_devices(
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get all trusted devices for the current user"""
    try:
        devices = await trusted_device_service.get_user_trusted_devices(
            db, 
            current_user_id
        )
        
        return TrustedDeviceList(
            devices=devices,
            total_count=len(devices)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trusted devices: {str(e)}"
        )

@router.delete("/trust-device/{device_id}")
async def revoke_trusted_device(
    device_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Revoke a specific trusted device"""
    try:
        success = await trusted_device_service.revoke_trusted_device(
            db, 
            current_user_id, 
            device_id
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Trusted device not found"
            )
        
        return {"message": "Trusted device revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke trusted device: {str(e)}"
        )

@router.delete("/trusted-devices/all")
async def revoke_all_trusted_devices(
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Revoke all trusted devices for the current user"""
    try:
        count = await trusted_device_service.revoke_all_trusted_devices(
            db, 
            current_user_id
        )
        
        return {
            "message": f"Revoked {count} trusted devices",
            "revoked_count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke trusted devices: {str(e)}"
        )

@router.get("/trusted-devices/check")
async def check_trusted_device(
    request: Request,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Check if current request is from a trusted device"""
    try:
        # Get token from cookie
        token = request.cookies.get("trusted_device_token")
        
        if not token:
            return {"is_trusted": False, "reason": "No trusted device token"}
        
        # Verify the token
        trusted_device = await trusted_device_service.verify_trusted_device(
            db=db,
            token=token,
            request=request,
            user_id=current_user_id
        )
        
        if trusted_device:
            return {
                "is_trusted": True,
                "device_name": trusted_device.device_name,
                "location": trusted_device.location,
                "expires_at": trusted_device.expires_at.isoformat()
            }
        else:
            return {"is_trusted": False, "reason": "Invalid or expired token"}
            
    except Exception as e:
        return {"is_trusted": False, "reason": f"Error checking trusted device: {str(e)}"} 