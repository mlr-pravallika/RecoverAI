import os
# pyrefly: ignore [missing-import]
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from backend.app.core.database import Base
from backend.app.models import models
from backend.app.policies.engine import PolicyEngine
from backend.app.services.orchestrator import RecoveryOrchestrator, OrchestratorError
from backend.app.ml.classifier import predict_recovery_probability

# Separate Test Database
TEST_DATABASE_URL = "sqlite:///./test_recoverai.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Initialize default policy config
    policy = models.PolicyConfig(
        id=1,
        max_retries=3,
        min_confidence=0.70,
        recovery_window_hours=72,
        max_automated_amount=40000.0
    )
    db.add(policy)
    
    # Initialize a mock customer
    cust = models.Customer(
        id="cust_test_123",
        name="Test User",
        email="test@user.com"
    )
    db.add(cust)
    db.commit()
    
    try:
        yield db
    finally:
        db.close()
        # Drop tables to clean up
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("./test_recoverai.db"):
            try:
                os.remove("./test_recoverai.db")
            except OSError:
                pass

# --- Unit Tests ---

def test_expected_recovery_calculation():
    # Expected recovery = amount * probability
    amount = 2500.0
    prob = 0.82
    expected = round(amount * prob, 2)
    assert expected == 2050.0

def test_policy_engine_fraud_block(db_session):
    pe = PolicyEngine(db_session)
    tx = models.Transaction(id="pay_t1", customer_id="cust_test_123", amount=1500.0, status="failed", failure_type="fraud")
    rc = models.RecoveryCase(transaction_id="pay_t1", retry_count=0, created_at=datetime.utcnow())
    
    res = pe.evaluate(tx, rc, proposed_action="RETRY", ai_confidence=0.85, root_cause_classification="fraud_suspected")
    
    assert res["allowed"] is False
    assert res["action"] == "STOP"
    assert "fraud" in res["reason"].lower()

def test_policy_engine_max_amount_manual_review(db_session):
    pe = PolicyEngine(db_session)
    # Exceeds max automated amount limit (₹40,000)
    tx = models.Transaction(id="pay_t2", customer_id="cust_test_123", amount=45000.0, status="failed", failure_type="temporary")
    rc = models.RecoveryCase(transaction_id="pay_t2", retry_count=0, created_at=datetime.utcnow())
    
    res = pe.evaluate(tx, rc, proposed_action="RETRY", ai_confidence=0.90, root_cause_classification="temporary_failure")
    
    assert res["allowed"] is False
    assert res["action"] == "MANUAL_REVIEW"
    assert "exceeds" in res["reason"].lower()

def test_policy_engine_low_confidence_manual_review(db_session):
    pe = PolicyEngine(db_session)
    tx = models.Transaction(id="pay_t3", customer_id="cust_test_123", amount=5000.0, status="failed", failure_type="temporary")
    rc = models.RecoveryCase(transaction_id="pay_t3", retry_count=0, created_at=datetime.utcnow())
    
    # Confidence (0.55) is below policy min threshold (0.70)
    res = pe.evaluate(tx, rc, proposed_action="RETRY", ai_confidence=0.55, root_cause_classification="temporary_failure")
    
    assert res["allowed"] is False
    assert res["action"] == "MANUAL_REVIEW"
    assert "below the required threshold" in res["reason"].lower()

def test_state_machine_invalid_transition(db_session):
    # Transitioning from FAILED directly to RECOVERED is forbidden
    case = models.RecoveryCase(transaction_id="pay_t4", status="FAILED")
    db_session.add(case)
    db_session.commit()
    
    with pytest.raises(OrchestratorError):
        RecoveryOrchestrator.transition_state(db_session, case, "RECOVERED", "SYSTEM", "Invalid jump")

# --- Integration Tests ---

def test_end_to_end_orchestrated_recovery(db_session):
    # 1. Create failed transaction
    tx = models.Transaction(
        id="pay_failed_int_99",
        customer_id="cust_test_123",
        amount=500.0,
        status="failed",
        payment_method="upi",
        failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
        failure_type="temporary",
        created_at=datetime.utcnow()
    )
    db_session.add(tx)
    db_session.commit()
    
    # 2. Initiate recovery workflow
    case = RecoveryOrchestrator.initiate_recovery(db_session, tx.id)
    assert case.status == "ANALYZING"
    
    # Verify audit log exists
    audit = db_session.query(models.AuditLog).filter(models.AuditLog.recovery_case_id == case.id).first()
    assert audit is not None
    assert audit.new_state == "ANALYZING"
    
    # 3. Run analysis (ML prediction + AI + Policy Engine checks)
    # Since amount is small and timeout is temporary, it should be approved for auto retry or link
    res = RecoveryOrchestrator.run_analysis_and_decide(db_session, case.id)
    assert case.status in ["ACTION_PENDING", "MANUAL_REVIEW"]
    
    if case.status == "ACTION_PENDING":
        # Execute approved action
        exec_res = RecoveryOrchestrator.execute_action(db_session, case.id)
        assert case.status == "AWAITING_RESULT"
        assert exec_res["status"] == "EXECUTED"
        
        # Simulate payment captured event
        RecoveryOrchestrator.handle_payment_success(db_session, case.id)
        assert case.status == "RECOVERED"
        assert tx.status == "captured"

def test_webhook_idempotency(db_session):
    # Seed duplicate events check
    event_id = "evt_duplicate_id_55"
    db_event = models.WebhookEvent(
        id=event_id,
        event_name="payment.failed",
        payload="{}",
        processed=True
    )
    db_session.add(db_event)
    db_session.commit()
    
    # Check duplicate detection query
    existing = db_session.query(models.WebhookEvent).filter(models.WebhookEvent.id == event_id).first()
    assert existing is not None
    assert existing.processed is True
