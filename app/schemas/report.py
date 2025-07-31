from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any, Dict

class ReportBase(BaseModel):
    month_id: str
    report_data: Dict[str, Any]
    total_income: float
    total_expense: float
    net_profit: float

class ReportCreate(ReportBase):
    user_id: int

class ReportUpdate(BaseModel):
    report_data: Dict[str, Any] | None = None
    total_income: float | None = None
    total_expense: float | None = None
    net_profit: float | None = None

class ReportResponse(ReportBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ReportRead(BaseModel):
    # ... fields ...
    model_config = ConfigDict(from_attributes=True) 