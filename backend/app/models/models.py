from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.core.database import Base

class Merchant(Base):
    __tablename__ = "merchants"
    
    id = Column(String, primary_key=True, index=True)
    business_name = Column(String, nullable=False)
    owner_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    razorpay_account_reference = Column(String, nullable=True)
    mode = Column(String, default="demo")  # demo, real
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="active")
    
    customers = relationship("Customer", back_populates="merchant")
    transactions = relationship("Transaction", back_populates="merchant")
    recovery_cases = relationship("RecoveryCase", back_populates="merchant")
    policy_configs = relationship("PolicyConfig", back_populates="merchant")
    webhook_events = relationship("WebhookEvent", back_populates="merchant")

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(String, primary_key=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.id", ondelete="CASCADE"), index=True, nullable=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    merchant = relationship("Merchant", back_populates="customers")
    transactions = relationship("Transaction", back_populates="customer")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.id", ondelete="CASCADE"), index=True, nullable=True)
    customer_id = Column(String, ForeignKey("customers.id"), index=True, nullable=False)
    order_id = Column(String, nullable=True)
    amount = Column(Float, nullable=False)  # stored in rupees / major currency unit
    currency = Column(String, default="INR")
    status = Column(String, index=True, default="created")  # created, failed, captured
    payment_method = Column(String, nullable=True)  # card, upi, netbanking, wallet
    failure_code = Column(String, nullable=True)
    failure_type = Column(String, nullable=True)
    is_demo = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    merchant = relationship("Merchant", back_populates="transactions")
    customer = relationship("Customer", back_populates="transactions")
    attempts = relationship("PaymentAttempt", back_populates="transaction")
    recovery_cases = relationship("RecoveryCase", back_populates="transaction")

class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    
    id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, ForeignKey("transactions.id"), index=True, nullable=False)
    attempt_number = Column(Integer, nullable=False)
    payment_method = Column(String, nullable=True)
    failure_code = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)
    status = Column(String, nullable=False)  # failed, captured
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transaction = relationship("Transaction", back_populates="attempts")

class RecoveryCase(Base):
    __tablename__ = "recovery_cases"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.id", ondelete="CASCADE"), index=True, nullable=True)
    transaction_id = Column(String, ForeignKey("transactions.id"), index=True, nullable=False)
    status = Column(String, default="FAILED", index=True)  # FAILED, ANALYZING, RECOVERY_ELIGIBLE, ACTION_PENDING, ACTION_EXECUTED, AWAITING_RESULT, RECOVERED, MANUAL_REVIEW, STOPPED
    recovery_probability = Column(Float, default=0.0)
    expected_recovery = Column(Float, default=0.0)
    recommended_action = Column(String, nullable=True)
    explanation = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    merchant = relationship("Merchant", back_populates="recovery_cases")
    transaction = relationship("Transaction", back_populates="recovery_cases")
    actions = relationship("RecoveryAction", back_populates="recovery_case")

class RecoveryAction(Base):
    __tablename__ = "recovery_actions"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    recovery_case_id = Column(Integer, ForeignKey("recovery_cases.id"), index=True, nullable=False)
    action_type = Column(String, nullable=False)  # RETRY, PAYMENT_LINK, REMINDER, MANUAL_REVIEW, STOP
    status = Column(String, default="PENDING")  # PENDING, EXECUTED, FAILED, CANCELLED
    details = Column(Text, nullable=True)  # JSON or descriptive text
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    recovery_case = relationship("RecoveryCase", back_populates="actions")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.id", ondelete="CASCADE"), index=True, nullable=True)
    transaction_id = Column(String, index=True, nullable=True)
    recovery_case_id = Column(Integer, index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    actor = Column(String, nullable=False)  # SYSTEM, AI, POLICY, ADMIN
    action = Column(String, nullable=False)
    previous_state = Column(String, nullable=True)
    new_state = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON string

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    
    id = Column(String, primary_key=True, index=True)  # razorpay event_id
    merchant_id = Column(String, ForeignKey("merchants.id", ondelete="CASCADE"), index=True, nullable=True)
    event_name = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    merchant = relationship("Merchant", back_populates="webhook_events")

class PolicyConfig(Base):
    __tablename__ = "policy_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.id", ondelete="CASCADE"), index=True, nullable=True)
    max_retries = Column(Integer, default=3)
    min_confidence = Column(Float, default=0.70)
    recovery_window_hours = Column(Integer, default=72)
    max_automated_amount = Column(Float, default=50000.0)  # e.g., 50k INR
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    merchant = relationship("Merchant", back_populates="policy_configs")

