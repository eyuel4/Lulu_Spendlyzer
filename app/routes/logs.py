from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
from datetime import datetime, timezone

from ..core.database import get_db
from ..models import User, SystemLog, AuditLog
from ..services.logging_service import logging_service
from ..schemas.logs import SystemLogResponse, AuditLogResponse, ErrorSummaryResponse, SystemLogRequest, AuditLogRequest
import os
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET environment variable must be set")
ALGORITHM = "HS256"

router = APIRouter(prefix="/logs", tags=["logs"])


async def get_current_user_superuser(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Get current user and verify superuser status"""
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
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check superuser status - handle SQLAlchemy column properly
        if not bool(user.is_superuser):
            raise HTTPException(status_code=403, detail="Access denied. Superuser required.")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_current_user_superuser: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/system", response_model=List[SystemLogResponse])
async def get_system_logs(
    level: Optional[str] = Query(None, description="Filter by log level"),
    category: Optional[str] = Query(None, description="Filter by category"),
    source: Optional[str] = Query(None, description="Filter by source"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    current_user: User = Depends(get_current_user_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get system logs with filtering options.
    Only superusers can access system logs.
    """
    
    logs = await logging_service.get_system_logs(
        level=level,
        category=category,
        source=source,
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    return logs


@router.get("/audit", response_model=List[AuditLogResponse])
async def get_audit_logs(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    current_user: User = Depends(get_current_user_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit logs with filtering options.
    Only superusers can access audit logs.
    """
    
    logs = await logging_service.get_audit_logs(
        event_type=event_type,
        resource_type=resource_type,
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    return logs


@router.get("/errors/summary", response_model=ErrorSummaryResponse)
async def get_error_summary(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get error summary statistics.
    Only superusers can access error summaries.
    """
    
    summary = await logging_service.get_error_summary(days=days)
    return summary


@router.get("/system/categories")
async def get_system_log_categories(
    current_user: User = Depends(get_current_user_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available system log categories for filtering.
    Only superusers can access this endpoint.
    """
    
    # This would typically query the database for distinct categories
    # For now, return a predefined list
    categories = [
        "AUTH", "EMAIL", "DATABASE", "API", "SYSTEM", 
        "PLAID", "NOTIFICATION", "SESSION", "FAMILY"
    ]
    
    return {"categories": categories}


@router.get("/audit/event-types")
async def get_audit_event_types(
    current_user: User = Depends(get_current_user_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available audit event types for filtering.
    Only superusers can access this endpoint.
    """
    
    # This would typically query the database for distinct event types
    # For now, return a predefined list
    event_types = [
        "LOGIN", "LOGOUT", "CREATE", "UPDATE", "DELETE", "VIEW",
        "PASSWORD_RESET", "EMAIL_CHANGE", "2FA_ENABLE", "2FA_DISABLE",
        "FAMILY_INVITE", "FAMILY_JOIN", "FAMILY_LEAVE"
    ]
    
    return {"event_types": event_types}


@router.post("/system")
async def create_system_log(
    log_data: SystemLogRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new system log entry.
    This endpoint is used by the frontend to log system errors.
    """
    try:
        # Get client IP from request
        client_ip = request.client.host if request.client else None
        
        # Log to the logging service
        await logging_service.log_system_error(
            title=log_data.title,
            message=log_data.message,
            error=None,  # Error details are in log_data.error_details
            category=log_data.category,
            source=log_data.source,
            user_id=log_data.user_id,
            session_id=log_data.session_id,
            request_id=log_data.request_id,
            endpoint=log_data.endpoint,
            method=log_data.method,
            ip_address=log_data.ip_address or client_ip,
            user_agent=log_data.user_agent,
            meta=log_data.meta,
            tags=log_data.tags
        )
        
        return {"message": "System log created successfully"}
        
    except Exception as e:
        print(f"Error creating system log: {e}")
        raise HTTPException(status_code=500, detail="Failed to create system log")


@router.post("/audit")
async def create_audit_log(
    audit_data: AuditLogRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new audit log entry.
    This endpoint is used by the frontend to log audit events.
    """
    try:
        # Get client IP from request
        client_ip = request.client.host if request.client else None
        
        # Log to the logging service
        await logging_service.log_audit_event(
            event_type=audit_data.event_type,
            resource_type=audit_data.resource_type,
            action=audit_data.action,
            user_id=audit_data.user_id,
            performed_by=audit_data.performed_by,
            resource_id=audit_data.resource_id,
            details=audit_data.details,
            changes=audit_data.changes,
            is_successful=audit_data.is_successful,
            failure_reason=audit_data.failure_reason,
            ip_address=audit_data.ip_address or client_ip,
            user_agent=audit_data.user_agent,
            session_id=audit_data.session_id,
            request_id=audit_data.request_id,
            meta=audit_data.meta
        )
        
        return {"message": "Audit log created successfully"}
        
    except Exception as e:
        print(f"Error creating audit log: {e}")
        raise HTTPException(status_code=500, detail="Failed to create audit log") 