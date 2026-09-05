# RecoverAI

> Turn failed payments into recoverable revenue.

RecoverAI is an AI-powered revenue recovery SaaS platform designed for track 3 of the Razorpay Buildathon. It detects failed checkouts, diagnoses decline codes, estimates recovery probabilities using an ML classifier, recommends bounded recovery actions (retries, payment links, manual reviews), applies deterministic compliance guardrails, handles Razorpay webhooks (with HMAC-SHA256 signature verification and idempotency), and tracks all actions in an immutable audit trail.

---

## Key Features

1. **Revenue Risk Engine**: Dynamic calculations of *Active Revenue at Risk*, *Expected Recovery (Yield)*, and *Recovery Success Rate* directly from transaction data.
2. **ML Recovery Classifier**: A Random Forest model (`backend/app/ml/model.joblib`) that predicts recovery chance based on amount, payment method, decline code, and customer success history.
3. **AI Decision Inspector**: Analyzes payment drops using Gemini (or a high-fidelity Mock fallback) and maps out the *Signal → History → ML Grade → AI Agent Rationale → Policy Engine → Action* flowchart.
4. **Deterministic Policy Engine**: Enforces guardrails such as maximum retries, amount limits, confidence thresholds, and immediate stops for fraud or expired cards.
5. **Recovery State Machine**: Implements explicit states (`FAILED`, `ANALYZING`, `RECOVERY_ELIGIBLE`, `ACTION_PENDING`, `ACTION_EXECUTED`, `AWAITING_RESULT`, `RECOVERED`, `MANUAL_REVIEW`, `STOPPED`) preventing invalid transitions.
6. **Batch Simulator**: Simulates processing hundreds of historical failures under different policy presets.
7. **What-If Analyzer**: Allows merchants to adjust variables interactively and forecast outcomes.
8. **Razorpay Webhook & Idempotency Receiver**: Implements cryptographic signature checks and prevents double-processing events.
9. **Timeline Audit Trail**: A compliance ledger logging every transition, actor (AI, Policy, System, Merchant), and rationale.

---

## Tech Stack

* **Frontend**: React, Vite, TypeScript, Tailwind CSS, Recharts, Lucide React.
* **Backend**: Python (3.12+), FastAPI, Uvicorn, SQLAlchemy, Pydantic, Pandas, Scikit-learn, joblib.
* **Database**: SQLAlchemy SQLite (local development fallback) and PostgreSQL support.

---

## Directory Structure

```
recoverai/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── core/         # Config, database setup
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Orchestrator, AI services, Razorpay client
│   │   ├── policies/     # Deterministic Policy Engine
│   │   ├── ml/           # Model training and live prediction classifier
│   │   ├── simulation/   # Batch & What-If simulation calculators
│   │   └── main.py       # Entry point
│   ├── requirements.txt
│   └── tests/            # Pytest suite
├── frontend/
│   ├── src/
│   │   ├── components/   # Metric cards, Sidebar, inspector
│   │   ├── pages/        # Dashboard, Queue, Simulator, What-If, Audit, Settings
│   │   ├── services/     # Fetch API client
│   │   ├── App.tsx       # Core layout
│   │   └── main.tsx      # Entry
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── vite.config.ts
├── data/
│   └── generate_dataset.py  # Synthetic data generator
├── docs/
│   ├── BUILD_STATUS.md
│   ├── DECISIONS.md
│   ├── architecture.md
│   └── demo-script.md
└── .env.example
```

---

## Setup & Running Locally

### Prerequisites
* Python 3.12+
* Node.js v18+ & npm

### 1. Environment Configuration
Copy `.env.example` to `.env` and configure credentials if available (defaults will fall back to simulated mock modes automatically):
```bash
cp .env.example .env
```

### 2. Backend Setup
1. Create a virtual environment and install packages:
   ```bash
   python -m venv .venv
   .venv/Scripts/activate # Windows
   pip install -r backend/requirements.txt
   ```
2. Populate the synthetic transaction database:
   ```bash
   python -m data.generate_dataset
   ```
3. Start the FastAPI Uvicorn server:
   ```bash
   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
   ```
   Verify at `http://localhost:8000/health`.

### 3. Frontend Setup
1. Navigate to the frontend directory and install npm packages:
   ```bash
   cd frontend
   npm install
   ```
2. Start the Vite React development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

---

## Verification & Testing

### Python Tests
Run the backend unit and integration test suite:
```bash
python -m pytest backend/tests/test_recoverai.py
```

### Frontend Build
Compile the production bundle to ensure no TypeScript or CSS errors:
```bash
cd frontend
npm run build
```

### Live Demo:
[RecoverAI Live Demo] https://frontend-seven-omega-k6nsl3ue7y.vercel.app — Explore the deployed RecoverAI revenue recovery platform.

### Product Demo:
[Product Demo Video] — Watch the end-to-end RecoverAI product workflow and key capabilities.

https://github.com/user-attachments/assets/975292dd-cc8d-4796-b605-33d65907a257

Product demonstration recording showcasing the RecoverAI platform, recovery workflow, simulations, policy controls, and auditability.




