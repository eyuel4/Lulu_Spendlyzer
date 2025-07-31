import asyncio
import traceback
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from ..models import SystemLog, AuditLog, User
from ..core.database import AsyncSessionLocal


class LoggingService:
    """
    Comprehensive logging service for system errors and audit trails.
    Handles async database persistence with proper error handling.
    """
    
    def __init__(self):
        self._log_queue = asyncio.Queue()
        self._audit_queue = asyncio.Queue()
        self._background_tasks = []
        self._is_running = False
    
    async def start(self):
        """Start background logging tasks"""
        if not self._is_running:
            self._is_running = True
            self._background_tasks = [
                asyncio.create_task(self._process_system_logs()),
                asyncio.create_task(self._process_audit_logs())
            ]
    
    async def stop(self):
        """Stop background logging tasks"""
        self._is_running = False
        for task in self._background_tasks:
            task.cancel()
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
    
    async def log_system_error(
        self,
        title: str,
        message: str,
        error: Optional[Exception] = None,
        category: str = "SYSTEM",
        source: str = "UNKNOWN",
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ):
        """
        Log a system error asynchronously
        """
        error_type = type(error).__name__ if error else None
        error_details = traceback.format_exc() if error else None
        
        log_entry = {
            "level": "ERROR",
            "category": category,
            "source": source,
            "title": title,
            "message": message,
            "error_type": error_type,
            "error_details": error_details,
            "user_id": user_id,
            "session_id": session_id,
            "request_id": request_id,
            "endpoint": endpoint,
            "method": method,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "meta": meta or {},
            "tags": tags or [],
            "created_at": datetime.utcnow()
        }
        
        await self._log_queue.put(log_entry)
        
        # Also log to console for immediate debugging
        print(f"System Error - {title}: {message}")
        if error:
            print(f"Error Type: {error_type}")
            print(f"Error Details: {error_details}")
    
    async def log_system_warning(
        self,
        title: str,
        message: str,
        category: str = "SYSTEM",
        source: str = "UNKNOWN",
        user_id: Optional[int] = None,
        meta: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ):
        """
        Log a system warning asynchronously
        """
        log_entry = {
            "level": "WARNING",
            "category": category,
            "source": source,
            "title": title,
            "message": message,
            "user_id": user_id,
            "meta": meta or {},
            "tags": tags or [],
            "created_at": datetime.utcnow()
        }
        
        await self._log_queue.put(log_entry)
        print(f"System Warning - {title}: {message}")
    
    async def log_system_info(
        self,
        title: str,
        message: str,
        category: str = "SYSTEM",
        source: str = "UNKNOWN",
        user_id: Optional[int] = None,
        meta: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ):
        """
        Log a system info message asynchronously
        """
        log_entry = {
            "level": "INFO",
            "category": category,
            "source": source,
            "title": title,
            "message": message,
            "user_id": user_id,
            "meta": meta or {},
            "tags": tags or [],
            "created_at": datetime.utcnow()
        }
        
        await self._log_queue.put(log_entry)
    
    async def log_audit_event(
        self,
        event_type: str,
        resource_type: str,
        action: str,
        user_id: Optional[int] = None,
        performed_by: Optional[int] = None,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        is_successful: str = "SUCCESS",
        failure_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ):
        """
        Log an audit event asynchronously
        """
        audit_entry = {
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "performed_by": performed_by,
            "action": action,
            "details": details,
            "changes": changes,
            "is_successful": is_successful,
            "failure_reason": failure_reason,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "session_id": session_id,
            "request_id": request_id,
            "meta": meta or {},
            "created_at": datetime.utcnow()
        }
        
        await self._audit_queue.put(audit_entry)
    
    async def log_failed_audit_event(
        self,
        event_type: str,
        resource_type: str,
        action: str,
        user_id: Optional[int],
        failure_reason: str,
        meta: Optional[dict] = None
    ):
        await self.log_audit_event(
            event_type=event_type,
            resource_type=resource_type,
            action=action,
            user_id=user_id,
            is_successful="FAILURE",
            failure_reason=failure_reason,
            meta=meta
        )
    
    async def _process_system_logs(self):
        """Background task to process system log queue"""
        while self._is_running:
            try:
                # Process up to 10 logs at a time
                logs_to_process = []
                for _ in range(10):
                    try:
                        log_entry = await asyncio.wait_for(self._log_queue.get(), timeout=1.0)
                        logs_to_process.append(log_entry)
                    except asyncio.TimeoutError:
                        break
                
                if logs_to_process:
                    await self._persist_system_logs(logs_to_process)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                print(f"Error processing system logs: {e}")
                await asyncio.sleep(1)  # Wait before retrying
    
    async def _process_audit_logs(self):
        """Background task to process audit log queue"""
        while self._is_running:
            try:
                # Process up to 10 audit entries at a time
                audit_entries = []
                for _ in range(10):
                    try:
                        audit_entry = await asyncio.wait_for(self._audit_queue.get(), timeout=1.0)
                        audit_entries.append(audit_entry)
                    except asyncio.TimeoutError:
                        break
                
                if audit_entries:
                    await self._persist_audit_logs(audit_entries)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                print(f"Error processing audit logs: {e}")
                await asyncio.sleep(1)  # Wait before retrying
    
    async def _persist_system_logs(self, logs: List[Dict[str, Any]]):
        """Persist system logs to database"""
        async with AsyncSessionLocal() as session:
            try:
                for log_data in logs:
                    system_log = SystemLog(**log_data)
                    session.add(system_log)
                
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                print(f"Error persisting system logs: {e}")
                # Fallback to console logging
                for log_data in logs:
                    print(f"Failed to persist log: {log_data}")
    
    async def _persist_audit_logs(self, audit_entries: List[Dict[str, Any]]):
        """Persist audit logs to database"""
        async with AsyncSessionLocal() as session:
            try:
                for audit_data in audit_entries:
                    audit_log = AuditLog(**audit_data)
                    session.add(audit_log)
                
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                print(f"Error persisting audit logs: {e}")
                # Fallback to console logging
                for audit_data in audit_entries:
                    print(f"Failed to persist audit: {audit_data}")
    
    async def get_system_logs(
        self,
        level: Optional[str] = None,
        category: Optional[str] = None,
        source: Optional[str] = None,
        user_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SystemLog]:
        """Retrieve system logs with filtering"""
        async with AsyncSessionLocal() as session:
            query = select(SystemLog).options(selectinload(SystemLog.user))
            
            if level:
                query = query.where(SystemLog.level == level)
            if category:
                query = query.where(SystemLog.category == category)
            if source:
                query = query.where(SystemLog.source == source)
            if user_id:
                query = query.where(SystemLog.user_id == user_id)
            
            query = query.order_by(desc(SystemLog.created_at)).offset(offset).limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_audit_logs(
        self,
        event_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        user_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Retrieve audit logs with filtering"""
        async with AsyncSessionLocal() as session:
            query = select(AuditLog).options(
                selectinload(AuditLog.user),
                selectinload(AuditLog.performer)
            )
            
            if event_type:
                query = query.where(AuditLog.event_type == event_type)
            if resource_type:
                query = query.where(AuditLog.resource_type == resource_type)
            if user_id:
                query = query.where(AuditLog.user_id == user_id)
            
            query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_error_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get error summary for the last N days"""
        async with AsyncSessionLocal() as session:
            # This would need a more complex query with date filtering
            # For now, return basic stats
            query = select(SystemLog).where(SystemLog.level == "ERROR")
            result = await session.execute(query)
            errors = result.scalars().all()
            
            return {
                "total_errors": len(errors),
                "errors_by_category": {},
                "errors_by_source": {},
                "recent_errors": errors[:10]  # Last 10 errors
            }


# Global logging service instance
logging_service = LoggingService() 