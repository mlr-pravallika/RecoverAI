# Razorpay Test Mode Sandbox Integration Guide

This guide details how to integrate **RecoverAI** with your **Razorpay Sandbox (Test Mode)** account to sync real checkout failures, verify credentials, configure hooks, and safely test recovery interventions.

---

## 1. Setup API Credentials

To query Razorpay Sandbox endpoints, the application reads parameters defined in the backend environment file.

Create or update `.env` in the root folder:

```bash
# Razorpay Test Mode Credentials
RAZORPAY_KEY_ID=rzp_test_XXXXXXXXXXXXXXXX
RAZORPAY_KEY_SECRET=YYYYYYYYYYYYYYYYYYYYYYYY
RAZORPAY_WEBHOOK_SECRET=ZZZZZZZZZZZZZZZZ
```

### 🔒 Safety Guardrails
* **Sandbox Verification**: If `RAZORPAY_KEY_ID` does not begin with `rzp_test_`, the payment service throws a security exception and blocks all requests. This ensures **zero real money is ever processed** under sandbox modes.
* **Credential Masking**: The backend never returns the secret key. The public `key_id` is masked in all JSON queries and rendered on the client as:
  `rzp_test_****[last 4 characters]`
* **Zero logs storage**: Actual API secrets are never printed, saved to database logs, or committed to version control.

---

## 2. API Status & Connection Verification

The Settings tab ("Policy Rules") displays integration status indicators:
- **API Status Dot**: The sidebar and settings page feature a connection status dot (`GET /api/integrations/razorpay/status`):
  * **Green (Connected)**: Active Sandbox keys configured and validated against Razorpay APIs.
  * **Red (Unconfigured)**: Credentials missing or rejected.
- **Verify Connection Action**: Clicking `Verify Connection` sends a mock status inquiry call. On success, it displays the masked Key ID.

---

## 3. Data Synchronization (`POST /api/integrations/razorpay/sync`)

The `Sync Test Data` action allows the merchant to import checkout failures directly from their Razorpay Sandbox ledger.

### Ingestion Logic:
1. **Fetch Payments**: Queries `/payments` from the Razorpay Sandbox API.
2. **Normalize and Filter**: Only fails (status = `failed`) are ingested. Amount values are converted from **paise** to **rupees** (divided by 100).
3. **Map Customers**: Customer profiles are mapped or created dynamically based on billing email metadata.
4. **Idempotent Checks**: The sync logic checks if transaction IDs already exist in the local SQLite database. Duplicate transactions are skipped, preserving manual reviews.
5. **Recovery Engine Start**: For newly discovered failures, the **ML Recovery Probability engine** evaluates the record and automatically spins up a case state machine.

---

## 4. Live Test Mode Toggle

Merchants can toggle between **Demo Mode** (synthetic checkout seeds) and **Live Test Mode** (real Sandbox ledger data).

* **Demo Mode**: The dashboard and Queue show mock transactions cloned under the newly registered merchant account on signup. Handy for quick features walkthroughs.
* **Live Test Mode**: Toggling to live mode updates the merchant preference on the backend database. The frontend immediately switches to query exclusively `is_demo = False` transactions synced from your Razorpay Sandbox account.
* **Badge Indicators**: The sidebar dynamically changes badges to **Real Test Mode** or **Demo Mode** depending on the active state.

---

## 5. Webhooks Ingestion (`POST /api/webhooks/razorpay`)

For automatic, real-time ingestion, configure your Razorpay developer dashboard to route events to the webhook receiver:

* **Event Listeners**: Listen for `payment.failed` and `payment.captured` event names.
* **HMAC Verification**: The webhook listener verifies the request payload using `x-razorpay-signature` and your local `RAZORPAY_WEBHOOK_SECRET` key via SHA256 HMAC digest validation.
* **Idempotency Safeguard**: Every incoming event ID is tracked in the `webhook_events` database log. Re-delivered webhook requests are skipped.
