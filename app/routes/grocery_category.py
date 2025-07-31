from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.grocery_category import GroceryCategoryCreate, GroceryCategoryUpdate, GroceryCategoryResponse
from typing import List

router = APIRouter(prefix="/grocery-categories", tags=["grocery_categories"])

@router.post("/", response_model=GroceryCategoryResponse)
def create_grocery_category(category: GroceryCategoryCreate, db: Session = Depends(get_db)):
    """Create a new grocery category."""
    pass

@router.get("/", response_model=List[GroceryCategoryResponse])
def list_grocery_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all grocery categories."""
    pass

@router.get("/{category_id}", response_model=GroceryCategoryResponse)
def get_grocery_category(category_id: int, db: Session = Depends(get_db)):
    """Get a grocery category by ID."""
    pass

@router.put("/{category_id}", response_model=GroceryCategoryResponse)
def update_grocery_category(category_id: int, category: GroceryCategoryUpdate, db: Session = Depends(get_db)):
    """Update a grocery category by ID."""
    pass

@router.delete("/{category_id}")
def delete_grocery_category(category_id: int, db: Session = Depends(get_db)):
    """Delete a grocery category by ID."""
    pass 