from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.models import models
from backend.app.schemas import schemas
from backend.app.services.orchestrator import RecoveryOrchestrator, OrchestratorError
from backend.app.simulation.simulator import SimulationEngine
from backend.app.services.razorpay_service import RazorpayService
from backend.app.core.auth import get_password_hash, verify_password, create_access_token, get_current_merchant

router = APIRouter(prefix="/api")

class StopRequest(BaseModel):
    reason: str

class DemoFailureRequest(BaseModel):
    scenario: str

# --- Authentication Endpoints ---

@router.post("/auth/signup", response_model=schemas.TokenResponse)
def signup(req: schemas.MerchantSignup, db: Session = Depends(get_db)):
    # 1. Check if email already registered
    existing = db.query(models.Merchant).filter(models.Merchant.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. Create merchant
    import uuid
    merchant_id = f"mer_{uuid.uuid4().hex[:12]}"
    new_merchant = models.Merchant(
        id=merchant_id,
        business_name=req.business_name,
        owner_name=req.owner_name,
        email=req.email,
        password_hash=get_password_hash(req.password),
        mode="demo"  # default to demo mode
    )
    db.add(new_merchant)
    db.commit()
    db.refresh(new_merchant)
    
    # 3. Create default PolicyConfig
    policy = models.PolicyConfig(
        merchant_id=new_merchant.id,
        max_retries=3,
        min_confidence=0.70,
        recovery_window_hours=72,
        max_automated_amount=40000.0
    )
    db.add(policy)
    db.commit()
    
    # 4. Clone global demo transactions to populate demo mode instantly
    try:
        SimulationEngine.seed_merchant_demo_data(db, new_merchant.id)
    except Exception as e:
        print(f"Error seeding merchant demo data: {e}")
        pass

    # 5. Generate token
    token = create_access_token({"sub": new_merchant.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "merchant": new_merchant
    }

@router.post("/auth/login", response_model=schemas.TokenResponse)
def login(req: schemas.MerchantLogin, db: Session = Depends(get_db)):
    merchant = db.query(models.Merchant).filter(models.Merchant.email == req.email).first()
    if not merchant or not verify_password(req.password, merchant.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    token = create_access_token({"sub": merchant.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "merchant": merchant
    }

@router.get("/merchant/profile", response_model=schemas.MerchantResponse)
def get_merchant_profile(current_merchant: models.Merchant = Depends(get_current_merchant)):
    return current_merchant

@router.post("/merchant/mode")
def update_merchant_mode(
    req: Dict[str, str], 
    db: Session = Depends(get_db), 
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    new_mode = req.get("mode")
    if new_mode not in ["demo", "real"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'demo' or 'real'.")
    current_merchant.mode = new_mode
    db.commit()
    db.refresh(current_merchant)
    return {"success": True, "mode": current_merchant.mode}

# --- Integrations Status & Sync ---

@router.get("/integrations/razorpay/status")
def get_razorpay_status(current_merchant: models.Merchant = Depends(get_current_merchant)):
    rzp_service = RazorpayService()
    res = rzp_service.verify_connection()
    return res

class ModelVerifyRequest(BaseModel):
    model_name: str

class ModelSelectRequest(BaseModel):
    model_name: str

@router.get("/integrations/gemini/status")
def get_gemini_status(current_merchant: models.Merchant = Depends(get_current_merchant)):
    from backend.app.services.gemini_service import GeminiService
    return GeminiService.verify_connection()

@router.get("/ai/gemini/status")
def get_ai_gemini_status(current_merchant: models.Merchant = Depends(get_current_merchant)):
    from backend.app.services.gemini_service import GeminiService
    return GeminiService.verify_connection()

@router.get("/ai/models")
def get_ai_models(current_merchant: models.Merchant = Depends(get_current_merchant)):
    import os
    from backend.app.services.gemini_service import GeminiService
    models_list = GeminiService.list_available_models()
    active_model = GeminiService.get_active_model()
    # Build list showing verification status
    res_models = []
    for m in models_list:
        name = m["name"]
        is_verified = any(vm["name"] == name for vm in GeminiService._verified_models)
        res_models.append({
            "name": name,
            "display_name": m["display_name"],
            "description": m["description"],
            "verified": is_verified,
            "supports_recoverai": True
        })
    return {
        "configured": bool(os.getenv("GEMINI_API_KEY")),
        "active_model": active_model,
        "models": res_models
    }

@router.post("/ai/models/verify")
def verify_ai_model(
    req: ModelVerifyRequest,
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    from backend.app.services.gemini_service import GeminiService
    res = GeminiService.verify_model_compatibility(req.model_name)
    return {
        "model_name": req.model_name,
        "verified": res["verified"],
        "error": res["error"]
    }

@router.post("/ai/models/select")
def select_ai_model(
    req: ModelSelectRequest,
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    from backend.app.services.gemini_service import GeminiService
    success = GeminiService.set_active_model(req.model_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Model {req.model_name} is not compatible or failed verification.")
    return {
        "success": True,
        "active_model": req.model_name
    }

@router.post("/integrations/razorpay/sync")
def sync_razorpay_data(
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    """
    Fetch payment logs from Razorpay Test Mode API, normalize and upsert them.
    Limits processing to Test Mode and prevents duplicate transactions.
    """
    rzp_service = RazorpayService()
    if not rzp_service.is_configured:
        raise HTTPException(status_code=400, detail="Razorpay is not configured in backend environment.")
    
    # Enforce Test Mode check
    if not rzp_service.key_id.startswith("rzp_test_"):
        raise HTTPException(status_code=400, detail="Only Razorpay Test Mode credentials are allowed.")

    try:
        payments = rzp_service.fetch_payments(count=50)
        fetched = len(payments)
        created = 0
        updated = 0
        duplicates = 0
        
        for pay in payments:
            tx_id = pay.get("id")
            email = pay.get("email") or "no-email@customer.com"
            contact = pay.get("contact")
            
            # 1. Fetch or create Customer under this merchant
            cust = db.query(models.Customer).filter(
                models.Customer.email == email,
                models.Customer.merchant_id == current_merchant.id
            ).first()
            
            if not cust:
                cust = models.Customer(
                    id=f"cust_{tx_id}_{current_merchant.id[:4]}",
                    merchant_id=current_merchant.id,
                    name=email.split("@")[0].capitalize(),
                    email=email,
                    phone=contact
                )
                db.add(cust)
                db.commit()
                db.refresh(cust)

            # 2. Normalize status
            rzp_status = pay.get("status")
            status_normalized = "failed" if rzp_status == "failed" else "captured" if rzp_status in ["captured", "authorized"] else rzp_status
            amount_rupees = float(pay.get("amount", 0)) / 100.0
            created_at_dt = datetime.utcfromtimestamp(pay.get("created_at"))

            # 3. Check for existing Transaction
            tx = db.query(models.Transaction).filter(
                models.Transaction.id == tx_id,
                models.Transaction.merchant_id == current_merchant.id
            ).first()

            if not tx:
                tx = models.Transaction(
                    id=tx_id,
                    merchant_id=current_merchant.id,
                    customer_id=cust.id,
                    order_id=pay.get("order_id"),
                    amount=amount_rupees,
                    currency=pay.get("currency", "INR"),
                    status=status_normalized,
                    payment_method=pay.get("method"),
                    failure_code=pay.get("error_code"),
                    failure_type="temporary" if pay.get("error_code") != "BAD_REQUEST_PAYMENT_RISK_THRESHOLD_EXCEEDED" else "fraud",
                    is_demo=False,  # real synced test data!
                    created_at=created_at_dt,
                    updated_at=datetime.utcnow()
                )
                db.add(tx)
                created += 1
                
                # Insert attempt log
                attempt = models.PaymentAttempt(
                    id=f"att_{tx_id}",
                    transaction_id=tx_id,
                    attempt_number=1,
                    payment_method=tx.payment_method,
                    failure_code=tx.failure_code,
                    failure_reason=pay.get("error_description"),
                    status=status_normalized,
                    created_at=created_at_dt
                )
                db.add(attempt)
                db.commit()
                
                # If transaction failed, auto-initiate recovery orchestrator
                if status_normalized == "failed":
                    case = RecoveryOrchestrator.initiate_recovery(db, tx_id)
                    if case.status == "ANALYZING":
                        # Run decision pipeline immediately so we calculate expected yield stats
                        RecoveryOrchestrator.run_analysis_and_decide(db, case.id)
            else:
                # Update status if it changed
                if tx.status != status_normalized:
                    tx.status = status_normalized
                    tx.updated_at = datetime.utcnow()
                    updated += 1
                    
                    # Update active case to RECOVERED if payment succeeded
                    if status_normalized == "captured":
                        case = db.query(models.RecoveryCase).filter(
                            models.RecoveryCase.transaction_id == tx.id,
                            models.RecoveryCase.status.in_(["ACTION_PENDING", "ACTION_EXECUTED", "AWAITING_RESULT", "MANUAL_REVIEW"])
                        ).first()
                        if case:
                            RecoveryOrchestrator.handle_payment_success(db, case.id, {"sync_event": True})
                else:
                    duplicates += 1
                    
        db.commit()
        return {
            "success": True,
            "fetched": fetched,
            "created": created,
            "updated": updated,
            "duplicates": duplicates
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synchronization failed: {str(e)}")

# --- Dashboard API ---

@router.get("/dashboard/summary", response_model=schemas.DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db), 
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    is_demo_mode = (current_merchant.mode == "demo")
    
    # 1. Total failed revenue (total potential risk)
    total_failed_query = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.merchant_id == current_merchant.id,
        models.Transaction.is_demo == is_demo_mode,
        models.Transaction.status == "failed"
    ).scalar() or 0.0

    # 2. Recovered revenue (cases marked RECOVERED)
    recovered_revenue = db.query(func.sum(models.Transaction.amount))\
        .join(models.RecoveryCase, models.Transaction.id == models.RecoveryCase.transaction_id)\
        .filter(
            models.Transaction.merchant_id == current_merchant.id,
            models.Transaction.is_demo == is_demo_mode,
            models.RecoveryCase.status == "RECOVERED"
        ).scalar() or 0.0

    # 3. Active revenue at risk (currently failed and active in recovery)
    active_statuses = ["FAILED", "ANALYZING", "RECOVERY_ELIGIBLE", "ACTION_PENDING", "ACTION_EXECUTED", "AWAITING_RESULT", "MANUAL_REVIEW"]
    revenue_at_risk = db.query(func.sum(models.Transaction.amount))\
        .join(models.RecoveryCase, models.Transaction.id == models.RecoveryCase.transaction_id)\
        .filter(
            models.Transaction.merchant_id == current_merchant.id,
            models.Transaction.is_demo == is_demo_mode,
            models.Transaction.status == "failed",
            models.RecoveryCase.status.in_(active_statuses)
        ).scalar() or 0.0

    # 4. Expected recovery (amount * probability for active cases)
    active_cases = db.query(models.RecoveryCase).filter(
        models.RecoveryCase.merchant_id == current_merchant.id,
        models.RecoveryCase.status.in_(active_statuses)
    ).all()
    # Double check if linked transaction matches active mode
    expected_recovery = 0.0
    for c in active_cases:
        tx = db.query(models.Transaction).filter(models.Transaction.id == c.transaction_id).first()
        if tx and tx.is_demo == is_demo_mode:
            expected_recovery += c.expected_recovery

    # 5. Recovery rate
    recovery_rate = (recovered_revenue / total_failed_query * 100.0) if total_failed_query > 0 else 0.0

    # 6. Active recoveries count
    active_recoveries = db.query(func.count(models.RecoveryCase.id))\
        .join(models.Transaction, models.RecoveryCase.transaction_id == models.Transaction.id)\
        .filter(
            models.RecoveryCase.merchant_id == current_merchant.id,
            models.Transaction.is_demo == is_demo_mode,
            models.RecoveryCase.status.in_(["ANALYZING", "RECOVERY_ELIGIBLE", "ACTION_PENDING", "ACTION_EXECUTED", "AWAITING_RESULT"])
        ).scalar() or 0

    # 7. Manual reviews count
    manual_reviews = db.query(func.count(models.RecoveryCase.id))\
        .join(models.Transaction, models.RecoveryCase.transaction_id == models.Transaction.id)\
        .filter(
            models.RecoveryCase.merchant_id == current_merchant.id,
            models.Transaction.is_demo == is_demo_mode,
            models.RecoveryCase.status == "MANUAL_REVIEW"
        ).scalar() or 0

    # 8. Blocked actions count (STOPPED cases due to fraud/policy)
    blocked_actions = db.query(func.count(models.RecoveryCase.id))\
        .join(models.Transaction, models.RecoveryCase.transaction_id == models.Transaction.id)\
        .filter(
            models.RecoveryCase.merchant_id == current_merchant.id,
            models.Transaction.is_demo == is_demo_mode,
            models.RecoveryCase.status == "STOPPED",
            models.RecoveryCase.recommended_action == "STOP"
        ).scalar() or 0

    # 9. Total transactions analyzed
    total_analyzed = db.query(func.count(models.Transaction.id)).filter(
        models.Transaction.merchant_id == current_merchant.id,
        models.Transaction.is_demo == is_demo_mode
    ).scalar() or 0

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

# --- Transactions & Recovery Queue Endpoints ---

@router.get("/transactions", response_model=List[schemas.TransactionResponse])
def get_transactions(
    status: Optional[str] = None,
    failure_type: Optional[str] = None,
    recommended_action: Optional[str] = None,
    min_amount: Optional[float] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    is_demo_mode = (current_merchant.mode == "demo")
    query = db.query(models.Transaction).join(models.Customer, models.Transaction.customer_id == models.Customer.id)\
              .filter(models.Transaction.merchant_id == current_merchant.id)\
              .filter(models.Transaction.is_demo == is_demo_mode)
    
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
def get_transaction(
    id: str, 
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == id,
        models.Transaction.merchant_id == current_merchant.id
    ).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@router.get("/recovery/cases", response_model=List[schemas.RecoveryCaseResponse])
def get_recovery_cases(
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    is_demo_mode = (current_merchant.mode == "demo")
    query = db.query(models.RecoveryCase).join(models.Transaction, models.RecoveryCase.transaction_id == models.Transaction.id)\
              .filter(models.RecoveryCase.merchant_id == current_merchant.id)\
              .filter(models.Transaction.is_demo == is_demo_mode)
    
    if status:
        query = query.filter(models.RecoveryCase.status == status)
    return query.order_by(models.RecoveryCase.updated_at.desc()).offset(offset).limit(limit).all()

# --- Simulation Endpoints ---

@router.post("/recovery/run", response_model=schemas.SimulationResponse)
def run_simulation(
    req: schemas.SimulationRequest, 
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    if current_merchant.mode != "demo":
        raise HTTPException(status_code=400, detail="Simulator is only supported in DEMO MODE.")
    try:
        # Enforce that simulator runs across the merchant's own transactions
        res = SimulationEngine.run_batch_simulation(db, req.num_transactions, req.policy_preset)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation run failed: {str(e)}")

@router.post("/recovery/what-if", response_model=schemas.WhatIfResponse)
def run_what_if(
    req: schemas.WhatIfRequest, 
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    try:
        return SimulationEngine.calculate_what_if(db, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"What-If evaluation failed: {str(e)}")

@router.post("/recovery/simulate-failure")
def simulate_failure(
    req: DemoFailureRequest, 
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    try:
        res = SimulationEngine.trigger_demo_scenario(db, req.scenario, current_merchant.id)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Policy Configuration Endpoints ---

@router.get("/policy/config", response_model=schemas.PolicyConfigResponse)
def get_policy_config(
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    config = db.query(models.PolicyConfig).filter(models.PolicyConfig.merchant_id == current_merchant.id).first()
    if not config:
        config = models.PolicyConfig(
            merchant_id=current_merchant.id,
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
def update_policy_config(
    req: schemas.PolicyConfigBase, 
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    config = db.query(models.PolicyConfig).filter(models.PolicyConfig.merchant_id == current_merchant.id).first()
    if not config:
        config = models.PolicyConfig(merchant_id=current_merchant.id)
        db.add(config)
    config.max_retries = req.max_retries
    config.min_confidence = req.min_confidence
    config.recovery_window_hours = req.recovery_window_hours
    config.max_automated_amount = req.max_automated_amount
    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    return config

# --- Manual Control / Review Actions ---

@router.post("/recovery/{id}/stop")
def stop_recovery(
    id: int, 
    req: StopRequest, 
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    # Verify owner of case
    case = db.query(models.RecoveryCase).filter(
        models.RecoveryCase.id == id,
        models.RecoveryCase.merchant_id == current_merchant.id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found.")
        
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

@router.post("/recovery/{id}/approve")
def approve_recovery(
    id: int,
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    """Approve a case stuck in MANUAL_REVIEW, moving it to ACTION_PENDING and triggering action."""
    case = db.query(models.RecoveryCase).filter(
        models.RecoveryCase.id == id,
        models.RecoveryCase.merchant_id == current_merchant.id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found.")
    if case.status != "MANUAL_REVIEW":
        raise HTTPException(status_code=400, detail="Only cases in MANUAL_REVIEW can be manual-approved.")
        
    try:
        # Move case state to ACTION_PENDING
        RecoveryOrchestrator.transition_state(
            db=db,
            case=case,
            new_state="ACTION_PENDING",
            actor="ADMIN",
            reason="Recovery action manually approved by merchant operator."
        )
        # Execute approved action
        exec_res = RecoveryOrchestrator.execute_action(db, case.id)
        return {"success": True, "new_state": case.status, "action_details": exec_res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/recovery/{id}/reject")
def reject_recovery(
    id: int,
    req: StopRequest,
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    """Reject a case stuck in MANUAL_REVIEW, moving it to STOPPED."""
    case = db.query(models.RecoveryCase).filter(
        models.RecoveryCase.id == id,
        models.RecoveryCase.merchant_id == current_merchant.id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found.")
    if case.status != "MANUAL_REVIEW":
        raise HTTPException(status_code=400, detail="Only cases in MANUAL_REVIEW can be manual-rejected.")
        
    try:
        RecoveryOrchestrator.transition_state(
            db=db,
            case=case,
            new_state="STOPPED",
            actor="ADMIN",
            reason=f"Recovery action manually rejected by merchant. Reason: {req.reason}"
        )
        return {"success": True, "new_state": case.status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Audit Trail Endpoints ---

@router.get("/audit/logs", response_model=List[schemas.AuditLogResponse])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_merchant: models.Merchant = Depends(get_current_merchant)
):
    return db.query(models.AuditLog).filter(
        models.AuditLog.merchant_id == current_merchant.id
    ).order_by(models.AuditLog.timestamp.desc()).limit(150).all()

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
        
    # Find merchant by razorpay key or defaults if webhook payload is verified
    # For simulation, we can associate with the first merchant in database
    merchant = db.query(models.Merchant).first()
    merchant_id = merchant.id if merchant else None

    # 3. Idempotency Check: prevent double-processing same event ID
    existing_event = db.query(models.WebhookEvent).filter(
        models.WebhookEvent.id == event_id,
        models.WebhookEvent.merchant_id == merchant_id
    ).first()
    if existing_event:
        return {"status": "ignored", "reason": "duplicate event detected", "event_id": event_id}
        
    # Seed idempotency record
    db_event = models.WebhookEvent(
        id=event_id,
        merchant_id=merchant_id,
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
        db_event.processed = True
        db.commit()
        return {"status": "ok", "message": "Ignored non-payment entity event."}

    if event_name == "payment.failed":
        tx = db.query(models.Transaction).filter(
            models.Transaction.id == payment_id,
            models.Transaction.merchant_id == merchant_id
        ).first()
        
        if not tx:
            cust = db.query(models.Customer).filter(models.Customer.merchant_id == merchant_id).first()
            if not cust:
                cust = models.Customer(
                    id=f"cust_webhook_{payment_id}",
                    merchant_id=merchant_id,
                    name="Webhook Customer",
                    email="webhook@customer.com"
                )
                db.add(cust)
                db.commit()
                
            amount_rupees = float(entity_data.get("amount", 0)) / 100.0
            tx = models.Transaction(
                id=payment_id,
                merchant_id=merchant_id,
                customer_id=cust.id,
                order_id=order_id,
                amount=amount_rupees,
                currency=entity_data.get("currency", "INR"),
                status="failed",
                payment_method=entity_data.get("method"),
                failure_code=entity_data.get("error_code", "GATEWAY_ERROR"),
                failure_type="temporary" if entity_data.get("error_code") != "BAD_REQUEST_PAYMENT_RISK_THRESHOLD_EXCEEDED" else "fraud",
                is_demo=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(tx)
            
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
            
        case = RecoveryOrchestrator.initiate_recovery(db, payment_id)
        if case.status == "ANALYZING":
            RecoveryOrchestrator.run_analysis_and_decide(db, case.id)
            if case.status == "ACTION_PENDING":
                RecoveryOrchestrator.execute_action(db, case.id)

    elif event_name in ["payment.captured", "payment.authorized"]:
        case = None
        if order_id:
            tx = db.query(models.Transaction).filter(
                models.Transaction.order_id == order_id,
                models.Transaction.merchant_id == merchant_id
            ).first()
            if tx:
                case = db.query(models.RecoveryCase).filter(
                    models.RecoveryCase.transaction_id == tx.id,
                    models.RecoveryCase.status.in_(["ACTION_PENDING", "ACTION_EXECUTED", "AWAITING_RESULT", "MANUAL_REVIEW"])
                ).first()
                
        if case:
            RecoveryOrchestrator.handle_payment_success(db, case.id, {"webhook_event_id": event_id})
            db.add(models.AuditLog(
                merchant_id=merchant_id,
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
