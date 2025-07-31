from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.category_override import CategoryOverrideCreate, CategoryOverrideUpdate, CategoryOverrideResponse
from typing import List

router = APIRouter(prefix="/category-overrides", tags=["category_overrides"])

@router.post("/", response_model=CategoryOverrideResponse)
def create_category_override(override: CategoryOverrideCreate, db: Session = Depends(get_db)):
    """Create a new category override."""
    pass

@router.get("/", response_model=List[CategoryOverrideResponse])
def list_category_overrides(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all category overrides."""
    pass

@router.get("/{override_id}", response_model=CategoryOverrideResponse)
def get_category_override(override_id: int, db: Session = Depends(get_db)):
    """Get a category override by ID."""
    pass

@router.put("/{override_id}", response_model=CategoryOverrideResponse)
def update_category_override(override_id: int, override: CategoryOverrideUpdate, db: Session = Depends(get_db)):
    """Update a category override by ID."""
    pass

@router.delete("/{override_id}")
def delete_category_override(override_id: int, db: Session = Depends(get_db)):
    """Delete a category override by ID."""
    pass 