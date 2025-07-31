from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.card import CardCreate, CardUpdate, CardResponse
from typing import List

router = APIRouter(prefix="/cards", tags=["cards"])

@router.post("/", response_model=CardResponse)
def create_card(card: CardCreate, db: Session = Depends(get_db)):
    """Create a new card."""
    pass

@router.get("/", response_model=List[CardResponse])
def list_cards(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all cards."""
    pass

@router.get("/{card_id}", response_model=CardResponse)
def get_card(card_id: int, db: Session = Depends(get_db)):
    """Get a card by ID."""
    pass

@router.put("/{card_id}", response_model=CardResponse)
def update_card(card_id: int, card: CardUpdate, db: Session = Depends(get_db)):
    """Update a card by ID."""
    pass

@router.delete("/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db)):
    """Delete a card by ID."""
    pass 