# RecoverAI — 5-Minute Demo Script

This script outlines the flow for a 5-minute demonstration of the RecoverAI platform.

---

## 0:00 - 0:45 | 1. The Problem & Landing Identity
* **Visual**: Show the **Overview Dashboard** homepage.
* **Script**:
  > "Hi everyone, I'm presenting **RecoverAI**—built for track 3 of the Razorpay Buildathon. 
  > Merchants lose millions to failed checkouts. But not all failures are permanent. RecoverAI finds revenue that is slipping away and wins it back safely.
  > Our tagline is simple: *'Turn failed payments into recoverable revenue.'*
  > On our Overview screen, you can see live metrics calculated directly from the transaction database: Active Revenue at Risk, expected recovery probabilities, actual recovered money, and active recoveries currently running."

## 0:45 - 1:30 | 2. Identifying Revenue Risk & The Queue
* **Visual**: Navigate to the **Recovery Queue** tab.
* **Script**:
  > "Let's click on the Recovery Queue. Here is the list of failed checkouts detected in our system. Each transaction lists customer contact details, amount, decline code, and our ML model's predicted recovery probability.
  > Let's search for a specific failed payment. We see a timeout payment on UPI. Clicking it slides out the **AI Decision Inspector**."

## 1:30 - 2:30 | 3. Explainability: Why Did We Make This Decision?
* **Visual**: Focus on the **AI Decision Inspector** slide-over panel.
* **Script**:
  > "The central question for any payment manager is: *'Why did RecoverAI make this decision?'*
  > The Inspector shows the exact chronological trace:
  > First, the failure signal arrives (`BAD_REQUEST_PAYMENT_TIMED_OUT`).
  > Second, we extract the customer's transaction history. In this case, they are a VIP returning user.
  > Third, our Random Forest classifier grades this with a recovery probability of 82%.
  > Fourth, the AI Decision Agent evaluates these features and recommends an automated `RETRY`.
  > Fifth, the deterministic Policy Engine audits the action, verifies it doesn't violate amount thresholds or retry limits, and approves the execution.
  > Every decision has an explainable reason generated dynamically."

## 2:30 - 3:30 | 4. Batch Recovery & The Simulator
* **Visual**: Navigate to the **Batch Simulator** tab.
* **Script**:
  > "Now let's demonstrate batch recovery across a large cohort of failed transactions.
  > We'll choose a cohort size of 250 failed payments under a 'Balanced' policy preset and click 'Run Bounded Recovery'.
  > You can watch the real-time progress bar execute. Under the hood, the orchestrator triggers the state machine, evaluates policy clearance, creates test-mode payment links, and simulates banking success outcomes.
  > And we're done! We analyzed ₹3.4L at risk, successfully recovered ₹1.8L, and our Policy Engine blocked 42 unsafe transactions due to fraud or card expirations."

## 3:30 - 4:15 | 5. Compliance & The Policy "What-If" Analyzer
* **Visual**: Navigate to the **What-If Analyzer** tab.
* **Script**:
  > "How does a merchant adjust their risk appetite? Let's open the What-If Analyzer.
  > By sliding the sliders, a merchant can change parameters like Min ML Confidence or Max Automated Amount.
  > The presets table immediately contrasts the custom rules against Conservative, Balanced, and Aggressive presets. 
  > If we lower the confidence threshold, we recover more revenue, but we increase manual outreach load and transaction fee overhead. RecoverAI gives the merchant absolute control."

## 4:15 - 5:00 | 6. Audit Trail & Webhook Verification
* **Visual**: Navigate to the **Audit Trail** tab, then show **Settings** tab.
* **Script**:
  > "Every single state transition, actor, and webhook event is captured in our chronological, read-only Security Audit Trail. 
  > Let's trigger a new failure under the Settings tab. Triggering 'Case A' simulates an incoming Razorpay webhook. The event arrives, is checked for HMAC signature validation, passes idempotency lookup to ignore duplicates, and immediately registers in the queue.
  > RecoverAI turns lost payments into recovered cash, safely and transparently. Thank you!"
