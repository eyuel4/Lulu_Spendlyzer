from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.billing import SubscriptionSchema, InvoiceSchema
from app.models.subscription import Subscription, Invoice
from datetime import datetime, timedelta
from typing import List, Optional

router = APIRouter(prefix="/billing", tags=["billing"])

@router.get("/summary", response_model=SubscriptionSchema)
def get_billing_summary(db: Session = Depends(get_db)):
    user_id = 1  # Replace with current user ID from auth
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if not subscription:
        return SubscriptionSchema(
            id=0,
            plan_name="Free Plan",
            status="inactive",
            renewal_date=None,
            payment_method=None,
            invoices=[]
        )
    invoices = [
        InvoiceSchema.from_orm(inv) for inv in subscription.invoices
    ]
    return SubscriptionSchema(
        id=getattr(subscription, 'id'),
        plan_name=getattr(subscription, 'plan_name'),
        status=getattr(subscription, 'status'),
        renewal_date=getattr(subscription, 'renewal_date'),
        payment_method=getattr(subscription, 'payment_method'),
        invoices=invoices
    )

@router.post("/subscribe")
def subscribe(
    plan_name: str = Body(...),
    payment_method: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    user_id = 1  # Replace with current user ID from auth
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if subscription:
        raise HTTPException(status_code=400, detail="Subscription already exists.")
    renewal_date = datetime.utcnow() + timedelta(days=30)
    new_sub = Subscription(
        user_id=user_id,
        plan_name=plan_name,
        status="active",
        renewal_date=renewal_date,
        payment_method=payment_method,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)
    return {"message": "Subscription started.", "subscription_id": new_sub.id}

@router.post("/update")
def update_subscription(
    plan_name: Optional[str] = Body(None),
    payment_method: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    user_id = 1  # Replace with current user ID from auth
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found.")
    if plan_name:
        subscription.plan_name = plan_name
    if payment_method:
        subscription.payment_method = payment_method
    subscription.updated_at = datetime.utcnow()
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return {"message": "Subscription updated."}

@router.post("/cancel")
def cancel_subscription(db: Session = Depends(get_db)):
    user_id = 1  # Replace with current user ID from auth
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found.")
    subscription.status = "canceled"
    subscription.updated_at = datetime.utcnow()
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return {"message": "Subscription canceled."} 