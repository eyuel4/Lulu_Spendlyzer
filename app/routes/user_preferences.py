from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from ..core.database import get_db
from ..core.auth import get_current_user_id
from ..models.user import UserPreferences
from ..models.user import User
from ..schemas.user_preferences import UserPreferencesResponse, UserPreferencesUpdate
from ..services.logging_service import logging_service

router = APIRouter(prefix="/user-preferences", tags=["user-preferences"])

@router.get("/", response_model=UserPreferencesResponse)
async def get_user_preferences(
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get user preferences for the current user"""
    try:
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user_id)
        )
        preferences = result.scalar_one_or_none()
        
        if not preferences:
            # Create default preferences if none exist
            preferences = UserPreferences(
                user_id=current_user_id,
                account_type='personal',
                primary_goal=['save_money'],
                financial_focus=['tracking'],
                experience_level='beginner',
                default_transaction_method=None,
                theme='light',
                notifications={
                    'email': True,
                    'push': True,
                    'sms': False
                },
                date_format='MM/DD/YYYY',
                currency='USD'
            )
            db.add(preferences)
            await db.commit()
            await db.refresh(preferences)
        
        await logging_service.log_audit_event(
            event_type="USER_ACTION",
            resource_type="USER_PREFERENCES",
            action="get_user_preferences",
            user_id=current_user_id,
            details="User retrieved their preferences"
        )
        
        return preferences
    except Exception as e:
        await db.rollback()
        await logging_service.log_audit_event(
            event_type="USER_ACTION",
            resource_type="USER_PREFERENCES",
            action="get_user_preferences_error",
            user_id=current_user_id,
            details=f"Error retrieving preferences: {str(e)}",
            is_successful="FAILURE"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user preferences"
        )

@router.patch("/", response_model=UserPreferencesResponse)
async def update_user_preferences(
    preferences_update: UserPreferencesUpdate,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update user preferences for the current user"""
    try:
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user_id)
        )
        preferences = result.scalar_one_or_none()
        
        if not preferences:
            # Create new preferences if none exist
            preferences = UserPreferences(user_id=current_user_id)
            db.add(preferences)
        
        # Update only the fields that are provided
        update_data = preferences_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(preferences, field, value)
        
        await db.commit()
        await db.refresh(preferences)
        
        await logging_service.log_audit_event(
            event_type="USER_ACTION",
            resource_type="USER_PREFERENCES",
            action="update_user_preferences",
            user_id=current_user_id,
            details=f"User updated preferences: {update_data}"
        )
        
        return preferences
    except Exception as e:
        await db.rollback()
        await logging_service.log_audit_event(
            event_type="USER_ACTION",
            resource_type="USER_PREFERENCES",
            action="update_user_preferences_error",
            user_id=current_user_id,
            details=f"Error updating preferences: {str(e)}",
            is_successful="FAILURE"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user preferences"
        )

@router.patch("/default-transaction-method", response_model=UserPreferencesResponse)
async def update_default_transaction_method(
    method: str,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update the default transaction method for the current user"""
    valid_methods = ['bank-api', 'upload-statement', 'manual']
    
    if method not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transaction method. Must be one of: {', '.join(valid_methods)}"
        )
    
    try:
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user_id)
        )
        preferences = result.scalar_one_or_none()
        
        if not preferences:
            # Create new preferences if none exist
            preferences = UserPreferences(
                user_id=current_user_id,
                account_type='personal',
                primary_goal=['save_money'],
                financial_focus=['tracking'],
                experience_level='beginner'
            )
            db.add(preferences)
        
        preferences.default_transaction_method = method
        await db.commit()
        await db.refresh(preferences)
        
        await logging_service.log_audit_event(
            event_type="USER_ACTION",
            resource_type="USER_PREFERENCES",
            action="update_default_transaction_method",
            user_id=current_user_id,
            details=f"User set default transaction method to: {method}"
        )
        
        return preferences
    except Exception as e:
        await db.rollback()
        await logging_service.log_audit_event(
            event_type="USER_ACTION",
            resource_type="USER_PREFERENCES",
            action="update_default_transaction_method_error",
            user_id=current_user_id,
            details=f"Error updating default transaction method: {str(e)}",
            is_successful="FAILURE"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update default transaction method"
        )
