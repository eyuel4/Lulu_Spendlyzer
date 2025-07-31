from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class SystemLogResponse(BaseModel):
    id: int
    level: str
    category: str
    source: str
    title: str
    message: str
    error_type: Optional[str] = None
    error_details: Optional[str] = None
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    environment: str = "development"
    meta: Dict[str, Any] = {}
    tags: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    event_type: str
    resource_type: str
    resource_id: Optional[str] = None
    user_id: Optional[int] = None
    performed_by: Optional[int] = None
    action: str
    details: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    is_successful: str = "SUCCESS"
    failure_reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    meta: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True


class ErrorSummaryResponse(BaseModel):
    total_errors: int
    errors_by_category: Dict[str, int]
    errors_by_source: Dict[str, int]
    recent_errors: List[SystemLogResponse]

    class Config:
        from_attributes = True


class LogFilterRequest(BaseModel):
    level: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    user_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


class AuditFilterRequest(BaseModel):
    event_type: Optional[str] = None
    resource_type: Optional[str] = None
    user_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


class SystemLogRequest(BaseModel):
    title: str
    message: str
    error_type: Optional[str] = None
    error_details: Optional[str] = None
    category: str = "SYSTEM"
    source: str = "UNKNOWN"
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class AuditLogRequest(BaseModel):
    event_type: str
    resource_type: str
    resource_id: Optional[str] = None
    user_id: Optional[int] = None
    performed_by: Optional[int] = None
    action: str
    details: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    is_successful: str = "SUCCESS"
    failure_reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None 