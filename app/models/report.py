from sqlalchemy import String, Column, Integer, Float, ForeignKey
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class Report(BaseModel):
    __tablename__ = "reports"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month_id = Column(String, nullable=False)
    report_data = Column(JSON, nullable=False)
    total_income = Column(Float, nullable=False)
    total_expense = Column(Float, nullable=False)
    net_profit = Column(Float, nullable=False)

    user = relationship("User", back_populates="reports") 