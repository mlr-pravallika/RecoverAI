from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import json
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.models import models
from backend.app.schemas import schemas
from backend.app.services.orchestrator import RecoveryOrchestrator
from backend.app.simulation.simulator import SimulationEngine
from backend.app.services.razorpay_service import RazorpayService

router = APIRouter(prefix="/api")

class StopRequest(BaseModel):
    reason: str

class DemoFailureRequest(BaseModel):
    scenario: str

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

# --- Simulation Endpoints ---

@router.post("/recovery/run", response_model=schemas.SimulationResponse)
def run_simulation(req: schemas.SimulationRequest, db: Session = Depends(get_db)):
    try:
        res = SimulationEngine.run_batch_simulation(db, req.num_transactions, req.policy_preset)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation run failed: {str(e)}")

@router.post("/recovery/what-if", response_model=schemas.WhatIfResponse)
def run_what_if(req: schemas.WhatIfRequest, db: Session = Depends(get_db)):
    try:
        return SimulationEngine.calculate_what_if(db, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"What-If evaluation failed: {str(e)}")

@router.post("/recovery/simulate-failure")
def simulate_failure(req: DemoFailureRequest, db: Session = Depends(get_db)):
    try:
        res = SimulationEngine.trigger_demo_scenario(db, req.scenario)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Policy Configuration Endpoints ---

@router.get("/policy/config", response_model=schemas.PolicyConfigResponse)
def get_policy_config(db: Session = Depends(get_db)):
    config = db.query(models.PolicyConfig).filter(models.PolicyConfig.id == 1).first()
    if not config:
        config = models.PolicyConfig(
            id=1,
            max_retries=3,
            min_confidence=0.70,
            recovery_window_hours=72,
            max_automated_amount=40000.0
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

@router.post("/policy/config", response_model=schemas.PolicyConfigResponse)
def update_policy_config(req: schemas.PolicyConfigBase, db: Session = Depends(get_db)):
    config = db.query(models.PolicyConfig).filter(models.PolicyConfig.id == 1).first()
    if not config:
        config = models.PolicyConfig(id=1)
        db.add(config)
    config.max_retries = req.max_retries
    config.min_confidence = req.min_confidence
    config.recovery_window_hours = req.recovery_window_hours
    config.max_automated_amount = req.max_automated_amount
    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    return config

# --- Manual Control Endpoints ---

@router.post("/recovery/{id}/stop")
def stop_recovery(id: int, req: StopRequest, db: Session = Depends(get_db)):
    try:
        case = RecoveryOrchestrator.cancel_recovery(db, id, req.reason)
        return {
            "status": "success",
            "case_id": case.id,
            "new_state": case.status,
            "message": "Recovery case aborted successfully."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Audit Trail Endpoints ---

@router.get("/audit/logs", response_model=List[schemas.AuditLogResponse])
def get_audit_logs(db: Session = Depends(get_db)):
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(150).all()

# --- Webhook receiver ---

@router.post("/webhooks/razorpay")
async def receive_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
    db: Session = Depends(get_db)
):
    """
    Accepts, validates, and processes Razorpay payment webhook events.
    Enforces signature verification and event-level idempotency checks.
    """
    raw_body = await request.body()
    
    # 1. Validate signature using HMAC-SHA256
    rzp_service = RazorpayService()
    if not rzp_service.verify_webhook_signature(raw_body, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature signature check failed.")

    # 2. Parse event payload
    try:
        event_payload = json.loads(raw_body.decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON request body.")
        
    event_id = event_payload.get("id")
    event_name = event_payload.get("event")
    
    if not event_id or not event_name:
        raise HTTPException(status_code=400, detail="Missing event metadata fields.")
        
    # 3. Idempotency Check: prevent double-processing same event ID
    existing_event = db.query(models.WebhookEvent).filter(models.WebhookEvent.id == event_id).first()
    if existing_event:
        return {"status": "ignored", "reason": "duplicate event detected", "event_id": event_id}
        
    # Seed idempotency record
    db_event = models.WebhookEvent(
        id=event_id,
        event_name=event_name,
        payload=raw_body.decode('utf-8'),
        processed=False,
        created_at=datetime.utcnow()
    )
    db.add(db_event)
    db.commit()
    
    # 4. Handle events
    entity_data = event_payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = entity_data.get("id")
    order_id = entity_data.get("order_id")
    
    if not payment_id:
        # Event is not related to a payment transaction
        db_event.processed = True
        db.commit()
        return {"status": "ok", "message": "Ignored non-payment entity event."}

    # Case A: payment.failed -> Trigger orchestrator recovery lifecycle
    if event_name == "payment.failed":
        # Look up or create failed transaction record
        tx = db.query(models.Transaction).filter(models.Transaction.id == payment_id).first()
        if not tx:
            # Create a mock customer for demo if missing
            cust = db.query(models.Customer).first()
            if not cust:
                cust = models.Customer(id="cust_webhook_generic", name="Webhook Customer", email="webhook@customer.com")
                db.add(cust)
                db.commit()
                
            amount_rupees = float(entity_data.get("amount", 0)) / 100.0
            tx = models.Transaction(
                id=payment_id,
                customer_id=cust.id,
                order_id=order_id,
                amount=amount_rupees,
                currency=entity_data.get("currency", "INR"),
                status="failed",
                payment_method=entity_data.get("method"),
                failure_code=entity_data.get("error_code", "GATEWAY_ERROR"),
                failure_type="temporary" if entity_data.get("error_code") != "BAD_REQUEST_PAYMENT_RISK_THRESHOLD_EXCEEDED" else "fraud",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(tx)
            
            # Add attempt log
            db.add(models.PaymentAttempt(
                id=f"att_webhook_{payment_id}",
                transaction_id=payment_id,
                attempt_number=1,
                payment_method=tx.payment_method,
                failure_code=tx.failure_code,
                failure_reason=entity_data.get("error_description"),
                status="failed",
                created_at=datetime.utcnow()
            ))
            db.commit()
            
        # Initiate recovery
        case = RecoveryOrchestrator.initiate_recovery(db, payment_id)
        # Execute decision pipeline immediately if status is ANALYZING
        if case.status == "ANALYZING":
            RecoveryOrchestrator.run_analysis_and_decide(db, case.id)
            if case.status == "ACTION_PENDING":
                RecoveryOrchestrator.execute_action(db, case.id)

    # Case B: payment.captured or payment.authorized -> Recover the case
    elif event_name in ["payment.captured", "payment.authorized"]:
        # Find active recovery case. It could be linked via order_id or reference_id.
        case = None
        if order_id:
            # Find transaction with this order_id
            tx = db.query(models.Transaction).filter(models.Transaction.order_id == order_id).first()
            if tx:
                case = db.query(models.RecoveryCase).filter(
                    models.RecoveryCase.transaction_id == tx.id,
                    models.RecoveryCase.status.in_(["ACTION_PENDING", "ACTION_EXECUTED", "AWAITING_RESULT", "MANUAL_REVIEW"])
                ).first()
                
        # Resolve case to RECOVERED
        if case:
            RecoveryOrchestrator.handle_payment_success(db, case.id, {"webhook_event_id": event_id})
            # Log audit trail
            db.add(models.AuditLog(
                transaction_id=case.transaction_id,
                recovery_case_id=case.id,
                timestamp=datetime.utcnow(),
                actor="SYSTEM",
                action="WEBHOOK_RESOLVED",
                reason=f"Payment webhook event '{event_name}' received. Transaction recovered successfully.",
                metadata_json=json.dumps({"payment_id": payment_id})
            ))
            db.commit()

    db_event.processed = True
    db.commit()
    return {"status": "ok", "event_id": event_id}
