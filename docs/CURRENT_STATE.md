# RecoverAI Current State Analysis

This document describes the existing codebase architecture of **RecoverAI** before the real-integration and productization upgrades.

---

## 1. Existing Architecture

### Frontend
- **Framework**: React 19 + TypeScript + Vite 8.
- **Styling**: Tailwind CSS v3.4.19 + PostCSS + Autoprefixer.
- **Routing**: Client-side state-based switcher inside `App.tsx` (conditional rendering based on `currentTab` state: `'overview' | 'queue' | 'simulator' | 'whatif' | 'audit' | 'settings'`).
- **Charts/Icons**: Recharts for data visualization; Lucide React for iconography.

### Backend
- **Framework**: FastAPI (Python 3.12+).
- **ORMs/DB**: SQLAlchemy with a local SQLite database (`recoverai.db`).
- **ML Engine**: Scikit-Learn Random Forest model (`model.joblib`) loaded inside `classifier.py` predicting transaction recovery probability.
- **AI Agent Layer**: `ai_service.py` houses `RootCauseAgent`, `RevenueRiskAgent`, `RecoveryDecisionAgent`, and `AIExplanationService` connecting to the Gemini 1.5 Flash API via raw JSON POST HTTP requests.
- **Policy Engine**: Deterministic veto rules check in `engine.py`.
- **Workflow State Machine**: Stateful coordinator in `orchestrator.py` transitioning cases through 9 distinct lifecycle states.

---

## 2. Existing Pages & Sidebar Tabs
- **Overview**: Metric summary cards (Revenue at Risk, Expected Recovery, Recovered Revenue, Success Rate) and Recharts charts (Intervention Distribution, Failure Code Ingestion).
- **Recovery Queue**: A tabular ledger of payment failures. Clicking a row slides open the AI Decision Inspector showing the detailed flowchart trace (Signal -> History -> ML Grade -> AI agent rationale -> Policy guardrails -> Final action).
- **Batch Simulator**: Simulates executing the orchestrator state machine across a batch cohort of 100-750 drops using `random.random() < ml_prob` for success/failure outcomes.
- **What-If Analyzer**: Dynamic sliders for max retries, min confidence, and max amount projecting expected yield against Conservative, Balanced, and Aggressive presets.
- **Audit Trail**: Chronological security audit log displaying state transitions, previous/new status values, actors, and metadata.
- **System Settings & Controls**: Form to save policy configuration limits and triggers for Case A through E simulation webhooks.

---

## 3. Existing database Schema
- `Customer` (id, name, email, phone, created_at)
- `Transaction` (id, customer_id, order_id, amount, currency, status, payment_method, failure_code, failure_type, created_at, updated_at)
- `PaymentAttempt` (id, transaction_id, attempt_number, payment_method, failure_code, failure_reason, status, created_at)
- `RecoveryCase` (id, transaction_id, status, recovery_probability, expected_recovery, recommended_action, retry_count, max_retries, created_at, updated_at)
- `RecoveryAction` (id, recovery_case_id, action_type, status, details, created_at, updated_at)
- `AuditLog` (id, transaction_id, recovery_case_id, timestamp, actor, action, previous_state, new_state, reason, metadata_json)
- `WebhookEvent` (id, event_name, payload, processed, created_at)
- `PolicyConfig` (id, max_retries, min_confidence, recovery_window_hours, max_automated_amount, updated_at)

---

## 4. Existing API Endpoints
- `GET /health`: Health-check.
- `GET /api/dashboard/summary`: Aggregated dashboard metrics.
- `GET /api/transactions`: Search, filter, and paginate transactions.
- `GET /api/transactions/{id}`: Detailed transaction data.
- `GET /api/recovery/cases`: List active cases.
- `POST /api/recovery/run`: Execute batch simulation.
- `POST /api/recovery/what-if`: Recalculate what-if projections.
- `POST /api/recovery/simulate-failure`: Seeder webhook scenario trigger.
- `GET /api/policy/config`: Get global configuration settings.
- `POST /api/policy/config`: Save global configuration settings.
- `POST /api/recovery/{id}/stop`: Manually stop a recovery workflow.
- `GET /api/audit/logs`: Retrieve audit trail ledger.
- `POST /api/webhooks/razorpay`: Razorpay webhook ingestion, HMAC validation, and idempotency check.

---

## 5. Mock/Demo Elements & Hardcoded Values
- **AI Fallback**: If `GEMINI_API_KEY` is not present, `ai_service.py` returns deterministic JSON structures for failure codes and VIP segment tags.
- **Razorpay fallback**: If credentials are missing in `.env`, `razorpay_service.py` returns a simulated payment link: `https://rzp.io/i/mock_plink...`.
- **System Health Statuses**: The frontend dashboard currently has no health indicators; they are hardcoded or not displayed.
- **Single Tenant**: No auth exists. All records are shared; `merchant_id` is missing in all tables.

---

## 6. Missing Production-Like Functionality
- **Merchant Authentication**: Signup, password hashing (bcrypt), login forms, protected client routes, sessions or JWT tokens, profile page, and logout action.
- **Multi-Tenant Isolation**: Database models and backend query filters must restrict access based on the logged-in merchant's `merchant_id`.
- **Real vs Demo Mode Flagging**: UI indicators to distinguish live Test Mode from local Demo Mode, and toggle mechanisms.
- **Real Google GenAI SDK integration**: Refactoring backend to use the modern `google-genai` package instead of legacy raw REST requests.
- **Live Health Status Checks**: Validating connections to SQLite DB, Razorpay APIs, Gemini APIs, and Webhook signatures.
- **Manual Review controls**: Merchant UI buttons to manual approve or reject cases stuck in the `MANUAL_REVIEW` queue.
