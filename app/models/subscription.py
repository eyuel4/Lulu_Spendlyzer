from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    plan_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default='inactive')  # 'active', 'inactive', 'canceled'
    renewal_date = Column(DateTime, nullable=True)
    payment_method = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    invoices = relationship('Invoice', back_populates='subscription')

class Invoice(Base):
    __tablename__ = 'invoices'

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=False, index=True)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False, default='Paid')  # 'Paid', 'Pending', 'Failed'

    subscription = relationship('Subscription', back_populates='invoices') 