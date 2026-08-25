# Design Decisions

## 1. Local SQLite Fallback
* **Decision**: Use SQLite for local development when `DATABASE_URL` is not specified or PostgreSQL is not reachable.
* **Rationale**: Avoid setting PostgreSQL as a hard blocker for installing/running the project locally. Using SQLAlchemy abstracts the differences seamlessly.

## 2. Gemini/Mock AI Fallback
* **Decision**: If `GEMINI_API_KEY` is not set, the AI services fall back to a high-fidelity mock AI implementation.
* **Rationale**: Ensures the product runs locally or in demo mode without credentials, providing realistic reasons and classifications.

## 3. Deterministic Policy Authority
* **Decision**: The LLM/AI recommends an action, but the deterministic Policy Engine has absolute veto/approver authority.
* **Rationale**: Financial actions require strict, audit-compliant guardrails. AI can err, but rules must be solid.

## 4. Single-Threaded or Process-Bounded State Transitions
* **Decision**: Store all state transitions in `AuditLog` and use transaction logs. Use database locks and constraints to ensure idempotency.
* **Rationale**: Prevent duplicate retries or link generations on simultaneous webhooks.
