from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any

# Health Schema
class HealthResponse(BaseModel):
    status: str
    service: str

# Customer Schema
class CustomerBase(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None

    class Config:
        from_attributes = True

# Payment Attempt Schema
class PaymentAttemptResponse(BaseModel):
    id: str
    transaction_id: str
    attempt_number: int
    payment_method: Optional[str] = None
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Recovery Action Schema
class RecoveryActionResponse(BaseModel):
    id: int
    recovery_case_id: int
    action_type: str
    status: str
    details: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Recovery Case Schema
class RecoveryCaseResponse(BaseModel):
    id: int
    transaction_id: str
    status: str
    recovery_probability: float
    expected_recovery: float
    recommended_action: Optional[str] = None
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime
    actions: List[RecoveryActionResponse] = []

    class Config:
        from_attributes = True

# Transaction Schema
class TransactionResponse(BaseModel):
    id: str
    customer_id: str
    order_id: Optional[str] = None
    amount: float
    currency: str
    status: str
    payment_method: Optional[str] = None
    failure_code: Optional[str] = None
    failure_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    customer: Optional[CustomerBase] = None
    attempts: List[PaymentAttemptResponse] = []
    recovery_cases: List[RecoveryCaseResponse] = []

    class Config:
        from_attributes = True

# Dashboard Summary Schema
class DashboardSummary(BaseModel):
    revenue_at_risk: float = 0.0
    expected_recovery: float = 0.0
    recovered_revenue: float = 0.0
    recovery_rate: float = 0.0
    active_recoveries: int = 0
    manual_reviews: int = 0
    blocked_actions: int = 0
    total_analyzed: int = 0

# Policy Config Schema
class PolicyConfigBase(BaseModel):
    max_retries: int = Field(default=3, ge=1, le=10)
    min_confidence: float = Field(default=0.70, ge=0.0, le=1.0)
    recovery_window_hours: int = Field(default=72, ge=1, le=168)
    max_automated_amount: float = Field(default=50000.0, ge=0.0)

class PolicyConfigResponse(PolicyConfigBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

# What-If Request
class WhatIfRequest(PolicyConfigBase):
    pass

# What-If Preset Response
class WhatIfPresetResult(BaseModel):
    preset_name: str
    max_retries: int
    min_confidence: float
    max_automated_amount: float
    recovery_rate: float
    recovered_revenue: float
    manual_review_rate: float
    blocked_actions_count: int

class WhatIfResponse(BaseModel):
    current: WhatIfPresetResult
    presets: List[WhatIfPresetResult]
    explanation: str

# Simulation Run Request
class SimulationRequest(BaseModel):
    num_transactions: int = Field(default=500, ge=10, le=1000)
    policy_preset: Optional[str] = "balanced"  # conservative, balanced, aggressive

# Simulation Run Response
class SimulationResponse(BaseModel):
    run_id: str
    transactions_analyzed: int
    revenue_at_risk: float
    recoverable_transactions: int
    actions_executed: int
    recovered_revenue: float
    recovery_rate: float
    manual_escalations: int
    unsafe_actions_prevented: int
    strategy_distribution: Dict[str, int]
    failure_distribution: Dict[str, int]

# Audit Log Schema
class AuditLogResponse(BaseModel):
    id: int
    transaction_id: Optional[str] = None
    recovery_case_id: Optional[int] = None
    timestamp: datetime
    actor: str
    action: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    reason: Optional[str] = None
    metadata_json: Optional[str] = None

    class Config:
        from_attributes = True
