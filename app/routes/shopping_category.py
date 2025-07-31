from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.shopping_category import ShoppingCategoryCreate, ShoppingCategoryUpdate, ShoppingCategoryResponse
from typing import List

router = APIRouter(prefix="/shopping-categories", tags=["shopping_categories"])

@router.post("/", response_model=ShoppingCategoryResponse)
def create_shopping_category(category: ShoppingCategoryCreate, db: Session = Depends(get_db)):
    """Create a new shopping category."""
    pass

@router.get("/", response_model=List[ShoppingCategoryResponse])
def list_shopping_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all shopping categories."""
    pass

@router.get("/{category_id}", response_model=ShoppingCategoryResponse)
def get_shopping_category(category_id: int, db: Session = Depends(get_db)):
    """Get a shopping category by ID."""
    pass

@router.put("/{category_id}", response_model=ShoppingCategoryResponse)
def update_shopping_category(category_id: int, category: ShoppingCategoryUpdate, db: Session = Depends(get_db)):
    """Update a shopping category by ID."""
    pass

@router.delete("/{category_id}")
def delete_shopping_category(category_id: int, db: Session = Depends(get_db)):
    """Delete a shopping category by ID."""
    pass 