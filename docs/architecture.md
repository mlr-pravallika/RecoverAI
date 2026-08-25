# RecoverAI Architecture Documentation

This document describes the system architecture, data models, AI workflow, state transitions, and webhook integrations of the **RecoverAI** platform.

---

## 1. System Topology

The diagram below outlines the overall component design of RecoverAI:

```mermaid
graph TD
    subgraph Frontend [React TypeScript Client]
        A[Overview Dashboard]
        B[Recovery Queue & Inspector]
        C[Simulator & What-If Panels]
    end

    subgraph Backend [FastAPI Modular Monolith]
        D[FastAPI REST API]
        E[Recovery Orchestrator]
        F[ML Classifier Engine]
        G[AI Agents Layer]
        H[Deterministic Policy Engine]
        I[Razorpay Client]
    end

    subgraph Storage [Database]
        J[(SQLAlchemy SQLite/PostgreSQL)]
    end

    subgraph External [Payment Gateway]
        K[Razorpay Test Mode APIs]
        L[Razorpay Webhook Event Source]
    end

    %% Flow lines
    A & B & C -->|Fetch / POST| D
    D -->|Coordinate Workflow| E
    E -->|Predict Probabilities| F
    E -->|Analyze Root Cause| G
    E -->|Evaluate Compliance| H
    E -->|Create Payment Links| I
    E & H & D -->|Query & Log| J
    I -->|Trigger Actions| K
    L -->|POST Webhooks| D
```

---

## 2. AI Decision Pipeline

Every failed checkout follows this evaluation pipeline:

```mermaid
flowchart TD
    A[Payment Failure Signal] --> B[Root Cause Agent]
    A --> C[Revenue Risk Agent]
    
    B -->|Diagnose: Temp/Perm/Fraud| D[Recovery Decision Agent]
    C -->|Extract: LTV Segment & Priority| D
    
    E[ML Random Forest Model] -->|Grade: 0% to 100% Probability| D
    
    D -->|Propose Action: RETRY / LINK / STOP| F[Deterministic Policy Engine]
    
    F -->|Veto Rules Checked| G{Rules Clearance?}
    G -->|Approved| H[ACTION_PENDING State]
    G -->|Veto Limit/Fraud| I[STOPPED State]
    G -->|Veto Confidence/Value| J[MANUAL_REVIEW State]
```

---

## 3. Recovery State Machine

The state machine manages the lifecycle of a recovery case with strict transition validations:

```mermaid
stateDiagram-v2
    [*] --> FAILED : Payment Failure Signal
    FAILED --> ANALYZING : analysis_initiated
    
    ANALYZING --> RECOVERY_ELIGIBLE : analysis_complete
    ANALYZING --> MANUAL_REVIEW : policy_confidence_veto
    ANALYZING --> STOPPED : policy_fraud_veto
    
    RECOVERY_ELIGIBLE --> ACTION_PENDING : action_approved
    RECOVERY_ELIGIBLE --> STOPPED : policy_veto
    RECOVERY_ELIGIBLE --> MANUAL_REVIEW : amount_veto
    
    ACTION_PENDING --> ACTION_EXECUTED : execute_intervention
    ACTION_PENDING --> STOPPED : manual_override
    
    ACTION_EXECUTED --> AWAITING_RESULT : action_completed
    
    AWAITING_RESULT --> RECOVERED : payment_success_webhook
    AWAITING_RESULT --> ACTION_PENDING : payment_failed_retry_eligible
    AWAITING_RESULT --> STOPPED : retry_limit_exhausted
    
    MANUAL_REVIEW --> ACTION_PENDING : merchant_approved
    MANUAL_REVIEW --> STOPPED : merchant_aborted
```

---

## 4. Webhook and Idempotency Flow

This flow protects the system against duplicate processing and out-of-order events:

```mermaid
sequenceDiagram
    autonumber
    participant Razorpay as Razorpay Event Source
    participant API as FastAPI Webhook Handler
    participant DB as SQLite DB
    participant SM as Orchestrator State Machine

    Razorpay->>API: POST /webhooks/razorpay (X-Razorpay-Signature)
    critical HMAC-SHA256 Signature Check
        API->>API: Recompute signature using raw body & Webhook Secret
    end
    alt Signature mismatch
        API-->>Razorpay: 400 Bad Request
    else Signature matched
        API->>DB: Check if Event ID exists in webhook_events
        alt Duplicate Event
            API-->>Razorpay: 200 OK (Duplicate ignored)
        else Fresh Event
            API->>DB: Insert Event ID (processed=False)
            API->>SM: Dispatch Event payload (payment.failed / payment.captured)
            SM->>DB: Update Case, Transaction state & Log Audit event
            API->>DB: Mark Event processed=True
            API-->>Razorpay: 200 OK
        end
    end
```
