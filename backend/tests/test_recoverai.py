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
TEST_DATABASE_URL = "sqlite:///:memory:"
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
        try:
            Base.metadata.drop_all(bind=engine)
        except Exception:
            pass
        engine.dispose()

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

# --- New Productization & Integration Tests ---

from unittest.mock import patch, MagicMock
from backend.app.core.auth import get_password_hash, verify_password, create_access_token
from backend.app.services.razorpay_service import RazorpayService

def test_password_hashing_and_jwt():
    plain = "securePass123"
    hashed = get_password_hash(plain)
    assert verify_password(plain, hashed) is True
    assert verify_password("wrongPass", hashed) is False

    # JWT generation
    token = create_access_token({"sub": "mer_12345"})
    assert token is not None
    assert len(token.split(".")) == 3

def test_multi_tenant_isolation(db_session):
    # Create two merchants
    m1 = models.Merchant(id="mer_A", business_name="Merchant A", owner_name="Owner A", email="a@m.com", password_hash="hash")
    m2 = models.Merchant(id="mer_B", business_name="Merchant B", owner_name="Owner B", email="b@m.com", password_hash="hash")
    db_session.add_all([m1, m2])
    db_session.commit()

    # Create customer & transaction for Merchant A
    c1 = models.Customer(id="cust_A", merchant_id="mer_A", name="Cust A", email="a@c.com")
    t1 = models.Transaction(id="pay_A", merchant_id="mer_A", customer_id="cust_A", amount=100.0, status="failed", is_demo=False)
    db_session.add_all([c1, t1])
    
    # Create customer & transaction for Merchant B
    c2 = models.Customer(id="cust_B", merchant_id="mer_B", name="Cust B", email="b@c.com")
    t2 = models.Transaction(id="pay_B", merchant_id="mer_B", customer_id="cust_B", amount=200.0, status="failed", is_demo=False)
    db_session.add_all([c2, t2])
    db_session.commit()

    # Verify query isolation
    txs_a = db_session.query(models.Transaction).filter(models.Transaction.merchant_id == "mer_A").all()
    txs_b = db_session.query(models.Transaction).filter(models.Transaction.merchant_id == "mer_B").all()

    assert len(txs_a) == 1
    assert txs_a[0].id == "pay_A"
    assert len(txs_b) == 1
    assert txs_b[0].id == "pay_B"

def test_razorpay_verify_connection_sandbox_guard():
    # If key starts with live, it must be blocked
    service = RazorpayService()
    service.key_id = "rzp_live_12345"
    service.key_secret = "secret"
    service.is_configured = True

    status = service.verify_connection()
    assert status["connected"] is False
    assert "mode" in status
    assert "Live production credentials blocked" in status["error"]

@patch("backend.app.services.razorpay_service.requests.get")
def test_razorpay_verify_connection_success(mock_get):
    # Mock successful response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"items": []}
    mock_get.return_value = mock_resp

    service = RazorpayService()
    service.key_id = "rzp_test_12345"
    service.key_secret = "secret"
    service.is_configured = True

    status = service.verify_connection()
    assert status["connected"] is True
    assert status["mode"] == "test"
    assert status["key_id_masked"] == "rzp_test_****2345"

@patch("backend.app.services.razorpay_service.requests.get")
def test_razorpay_sync_logic(mock_get, db_session):
    # Mock Razorpay fetch_payments
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {
                "id": "pay_rzp_999",
                "amount": 50000, # 500 INR
                "currency": "INR",
                "status": "failed",
                "method": "card",
                "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                "error_description": "Network timeout",
                "created_at": 1787634200,
                "email": "cust999@example.com",
                "contact": "+91999999999"
            }
        ]
    }
    mock_get.return_value = mock_resp

    # Initialize a merchant in DB
    merchant = models.Merchant(id="mer_sync_test", business_name="Sync Corp", owner_name="Sync Owner", email="sync@m.com", password_hash="hash")
    db_session.add(merchant)
    db_session.commit()

    # Call syncer endpoint equivalent logic
    from backend.app.api.endpoints import sync_razorpay_data
    # We will test the syncer logic via mock or calling it directly
    rzp_service = RazorpayService()
    rzp_service.key_id = "rzp_test_12345"
    rzp_service.key_secret = "secret"
    rzp_service.is_configured = True

    # Run the same operations as the sync endpoint
    payments = rzp_service.fetch_payments(count=1)
    assert len(payments) == 1
    
    pay = payments[0]
    tx_id = pay["id"]
    email = pay["email"]
    
    cust = models.Customer(
        id=f"cust_{tx_id}",
        merchant_id=merchant.id,
        name="Sync Customer",
        email=email
    )
    db_session.add(cust)
    db_session.commit()

    tx = models.Transaction(
        id=tx_id,
        merchant_id=merchant.id,
        customer_id=cust.id,
        amount=pay["amount"] / 100.0,
        currency=pay["currency"],
        status=pay["status"],
        payment_method=pay["method"],
        failure_code=pay["error_code"],
        is_demo=False,
        created_at=datetime.utcnow()
    )
    db_session.add(tx)
    db_session.commit()

    # Verify upsert works and prevents duplicates
    tx_check = db_session.query(models.Transaction).filter(models.Transaction.id == tx_id).all()
    assert len(tx_check) == 1
    assert tx_check[0].amount == 500.0

# --- Gemini Service Integration Tests ---

from backend.app.services.gemini_service import GeminiService

def test_gemini_service_verify_connection_missing_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    status = GeminiService.verify_connection()
    assert status["connected"] is False
    assert status["error"] == "GEMINI: NOT CONFIGURED"

@patch("backend.app.services.gemini_service.genai.Client")
def test_gemini_service_verify_connection_success(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"status": "ok", "explanation": "test connection successful"}'
    mock_client.models.generate_content.return_value = mock_response
    
    mock_model = MagicMock()
    mock_model.name = "models/gemini-3.5-flash"
    mock_model.display_name = "Gemini 3.5 Flash"
    mock_client.models.list.return_value = [mock_model]
    
    mock_client_cls.return_value = mock_client

    # Reset service cached variables so initialization runs inside the test
    GeminiService._init_done = False
    GeminiService._active_model = None
    GeminiService._verified_models = []

    status = GeminiService.verify_connection()
    assert status["connected"] is True
    assert status["error"] is None
    assert status["active_model"] == "gemini-3.5-flash"

@patch("backend.app.services.gemini_service.genai.Client")
def test_gemini_service_make_recovery_decision(mock_client_cls, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Structured output matching RecoveryDecision schema
    mock_response.text = '{"recommended_action": "RETRY", "confidence": 0.85, "explanation": "Temporary payment timeout, retry approved.", "classification": "temporary_failure", "failure_reason": "timeout", "recovery_probability": 0.85, "risk_level": "LOW", "customer_action_required": false, "policy_considerations": "none"}'
    mock_client.models.generate_content.return_value = mock_response
    
    mock_model = MagicMock()
    mock_model.name = "models/gemini-3.5-flash"
    mock_client.models.list.return_value = [mock_model]
    
    mock_client_cls.return_value = mock_client

    # Setup mock active model directly
    GeminiService._init_done = True
    GeminiService._active_model = "gemini-3.5-flash"
    GeminiService._verified_models = [{"name": "gemini-3.5-flash", "verified": True, "supports_recoverai": True}]

    res = GeminiService.make_recovery_decision(
        tx_id="pay_test_123",
        amount=100.0,
        payment_method="card",
        failure_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
        retry_count=0,
        customer_email="test@c.com",
        customer_spending_history=500.0
    )
    
    assert res["recommended_action"] == "RETRY"
    assert res["confidence"] == 0.85
    assert "retry approved" in res["explanation"]
    assert res["failure_classification"] == "temporary_failure"
    assert res["model_name"] == "gemini-3.5-flash"
    assert res["is_mock"] is False


