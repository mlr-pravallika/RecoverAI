from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.models import models
from backend.app.schemas import schemas

router = APIRouter(prefix="/api")

@router.get("/dashboard/summary", response_model=schemas.DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    # 1. Total failed revenue (total potential risk)
    total_failed_query = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.status == "failed"
    ).scalar() or 0.0

    # 2. Recovered revenue (cases marked RECOVERED)
    recovered_revenue = db.query(func.sum(models.Transaction.amount))\
        .join(models.RecoveryCase, models.Transaction.id == models.RecoveryCase.transaction_id)\
        .filter(models.RecoveryCase.status == "RECOVERED")\
        .scalar() or 0.0

    # 3. Active revenue at risk (currently failed and active in recovery)
    active_statuses = ["FAILED", "ANALYZING", "RECOVERY_ELIGIBLE", "ACTION_PENDING", "ACTION_EXECUTED", "AWAITING_RESULT", "MANUAL_REVIEW"]
    revenue_at_risk = db.query(func.sum(models.Transaction.amount))\
        .join(models.RecoveryCase, models.Transaction.id == models.RecoveryCase.transaction_id)\
        .filter(models.Transaction.status == "failed")\
        .filter(models.RecoveryCase.status.in_(active_statuses))\
        .scalar() or 0.0

    # 4. Expected recovery (amount * probability for active cases)
    active_cases = db.query(models.RecoveryCase).filter(models.RecoveryCase.status.in_(active_statuses)).all()
    expected_recovery = sum(c.expected_recovery for c in active_cases)

    # 5. Recovery rate
    recovery_rate = (recovered_revenue / total_failed_query * 100.0) if total_failed_query > 0 else 0.0

    # 6. Active recoveries count
    active_recoveries = db.query(func.count(models.RecoveryCase.id)).filter(
        models.RecoveryCase.status.in_(["ANALYZING", "RECOVERY_ELIGIBLE", "ACTION_PENDING", "ACTION_EXECUTED", "AWAITING_RESULT"])
    ).scalar() or 0

    # 7. Manual reviews count
    manual_reviews = db.query(func.count(models.RecoveryCase.id)).filter(
        models.RecoveryCase.status == "MANUAL_REVIEW"
    ).scalar() or 0

    # 8. Blocked actions count (STOPPED cases due to fraud/policy)
    # We can detect blocked actions in audit logs or RecoveryCases that have recommended_action "STOP" and status "STOPPED"
    blocked_actions = db.query(func.count(models.RecoveryCase.id)).filter(
        models.RecoveryCase.status == "STOPPED",
        models.RecoveryCase.recommended_action == "STOP"
    ).scalar() or 0

    # 9. Total transactions analyzed
    total_analyzed = db.query(func.count(models.Transaction.id)).scalar() or 0

    return schemas.DashboardSummary(
        revenue_at_risk=round(revenue_at_risk, 2),
        expected_recovery=round(expected_recovery, 2),
        recovered_revenue=round(recovered_revenue, 2),
        recovery_rate=round(recovery_rate, 2),
        active_recoveries=active_recoveries,
        manual_reviews=manual_reviews,
        blocked_actions=blocked_actions,
        total_analyzed=total_analyzed
    )

@router.get("/transactions", response_model=List[schemas.TransactionResponse])
def get_transactions(
    status: Optional[str] = None,
    failure_type: Optional[str] = None,
    recommended_action: Optional[str] = None,
    min_amount: Optional[float] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(models.Transaction).join(models.Customer, models.Transaction.customer_id == models.Customer.id)
    
    if status:
        query = query.filter(models.Transaction.status == status)
    if failure_type:
        query = query.filter(models.Transaction.failure_type == failure_type)
    if min_amount:
        query = query.filter(models.Transaction.amount >= min_amount)
    if recommended_action:
        query = query.join(models.RecoveryCase, models.Transaction.id == models.RecoveryCase.transaction_id)\
                     .filter(models.RecoveryCase.recommended_action == recommended_action)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (models.Transaction.id.like(search_pattern)) | 
            (models.Customer.name.like(search_pattern)) | 
            (models.Customer.email.like(search_pattern))
        )
        
    # Order by newest transactions first
    transactions = query.order_by(models.Transaction.created_at.desc()).offset(offset).limit(limit).all()
    return transactions

@router.get("/transactions/{id}", response_model=schemas.TransactionResponse)
def get_transaction(id: str, db: Session = Depends(get_db)):
    transaction = db.query(models.Transaction).filter(models.Transaction.id == id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@router.get("/recovery/cases", response_model=List[schemas.RecoveryCaseResponse])
def get_recovery_cases(
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(models.RecoveryCase)
    if status:
        query = query.filter(models.RecoveryCase.status == status)
    return query.order_by(models.RecoveryCase.updated_at.desc()).offset(offset).limit(limit).all()
