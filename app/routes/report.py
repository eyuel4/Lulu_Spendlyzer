from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.report import ReportCreate, ReportUpdate, ReportResponse
from typing import List

router = APIRouter(prefix="/reports", tags=["reports"])

@router.post("/", response_model=ReportResponse)
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    """Create a new report."""
    pass

@router.get("/", response_model=List[ReportResponse])
def list_reports(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all reports."""
    pass

@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    """Get a report by ID."""
    pass

@router.put("/{report_id}", response_model=ReportResponse)
def update_report(report_id: int, report: ReportUpdate, db: Session = Depends(get_db)):
    """Update a report by ID."""
    pass

@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    """Delete a report by ID."""
    pass 