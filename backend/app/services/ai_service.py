import os
import json
import requests
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models import models
from backend.app.ml.classifier import predict_recovery_probability

class AIAgentBase:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.use_mock = not bool(self.api_key.strip())
        if self.use_mock:
            print("GEMINI_API_KEY not found. Running AI Agents in MOCK / DEMO mode.")
        else:
            print("GEMINI_API_KEY found. Running AI Agents in GEMINI LIVE mode.")

    def _call_gemini(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if self.use_mock:
            return None
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        # Structure the payload with system instructions and JSON request
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                resp_json = response.json()
                text_content = resp_json['candidates'][0]['content']['parts'][0]['text']
                # Parse JSON output from LLM
                return json.loads(text_content.strip())
            else:
                print(f"Gemini API returned status code {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return None

class RootCauseAgent(AIAgentBase):
    def analyze_failure(self, failure_code: str, payment_method: str, attempt_details: str) -> Dict[str, Any]:
        """Classify failure root cause: temporary_failure, permanent_failure, or fraud_suspected."""
        if self.use_mock:
            # Deterministic mock responses based on official Razorpay failure codes
            if failure_code == "BAD_REQUEST_PAYMENT_RISK_THRESHOLD_EXCEEDED":
                return {
                    "classification": "fraud_suspected",
                    "confidence": 0.98,
                    "root_cause": "Razorpay risk rules flagged the payment card as suspicious."
                }
            elif failure_code == "BAD_REQUEST_PAYMENT_CARD_EXPIRED":
                return {
                    "classification": "permanent_failure",
                    "confidence": 0.95,
                    "root_cause": "The customer's card is expired and cannot be retried."
                }
            elif failure_code == "GATEWAY_ERROR":
                return {
                    "classification": "temporary_failure",
                    "confidence": 0.92,
                    "root_cause": "Network gateway timeout between Razorpay and the issuing bank."
                }
            else:
                return {
                    "classification": "temporary_failure",
                    "confidence": 0.82,
                    "root_cause": f"Temporary customer side transaction drop ({failure_code})."
                }

        # Live Gemini logic
        prompt = f"""
        Analyze this payment failure signal and classify it.
        Failure Code: {failure_code}
        Payment Method: {payment_method}
        Attempt Details: {attempt_details}
        
        Respond ONLY with a JSON object matching this schema:
        {{
          "classification": "temporary_failure" | "permanent_failure" | "fraud_suspected",
          "confidence": 0.0 to 1.0,
          "root_cause": "Brief explanation of the root cause"
        }}
        """
        result = self._call_gemini(prompt)
        if result and "classification" in result:
            return result
        # Fallback if parse fails
        return {
            "classification": "temporary_failure" if failure_code != "BAD_REQUEST_PAYMENT_RISK_THRESHOLD_EXCEEDED" else "fraud_suspected",
            "confidence": 0.50,
            "root_cause": "Fallback root-cause classification due to API parser timeout."
        }

class RevenueRiskAgent(AIAgentBase):
    def assess_risk(self, amount: float, customer_id: str, db: Session) -> Dict[str, Any]:
        """Assess the priority of recovery based on transaction volume, history, and customer value."""
        # Query customer info
        customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
        name = customer.name if customer else "Unknown"
        
        # Query total customer transactions to establish LTV
        history_txs = db.query(models.Transaction).filter(models.Transaction.customer_id == customer_id).all()
        total_spent = sum(t.amount for t in history_txs if t.status == "captured")
        success_count = sum(1 for t in history_txs if t.status == "captured")
        
        # Heuristics for mock
        priority = "LOW"
        if amount > 15000:
            priority = "HIGH"
        elif success_count > 3:
            priority = "MEDIUM"
            
        return {
            "customer_ltv": float(total_spent),
            "customer_loyalty_segment": "VIP" if success_count > 5 else "Returning" if success_count > 1 else "New",
            "recovery_priority": priority
        }

class RecoveryDecisionAgent(AIAgentBase):
    def make_decision(
        self,
        amount: float,
        root_cause: str,
        ml_prob: float,
        priority: str,
        retry_count: int
    ) -> Dict[str, Any]:
        """Formulate recommendation: RETRY, PAYMENT_LINK, MANUAL_REVIEW, or STOP."""
        # Simple deterministic Mock Decision mapping
        if root_cause == "fraud_suspected":
            return {
                "recommended_action": "STOP",
                "confidence": 0.99,
                "reason": "Compliance policy strictly prohibits retrying potential fraud attempts."
            }
        
        if root_cause == "permanent_failure":
            return {
                "recommended_action": "STOP",
                "confidence": 0.90,
                "reason": "Permanent decline reason. Automated retries will fail. Recommend stopping."
            }
            
        if retry_count >= 3:
            return {
                "recommended_action": "STOP",
                "confidence": 0.95,
                "reason": "Max automatic retry limit (3 attempts) has been exhausted."
            }

        # Otherwise, choose action based on ML probability & value
        if ml_prob >= 0.70:
            if amount > 30000:
                action = "MANUAL_REVIEW"
                reason = "High recovery probability, but transaction amount exceeds automated retry threshold. Needs supervisor sign-off."
            else:
                action = "RETRY"
                reason = "High recovery probability (ML Model) with temporary decline code. Approved for automated background retry."
        elif ml_prob >= 0.20:
            if amount > 15000:
                action = "MANUAL_REVIEW"
                reason = "Medium recovery probability. Large transaction amount requires manual outreach."
            else:
                action = "PAYMENT_LINK"
                reason = "Medium recovery probability. Sending automated payment link to customer's email and phone."
        else:
            action = "STOP"
            reason = "Very low recovery probability. Customer payment history shows consecutive declines. Stop intervention."

        return {
            "recommended_action": action,
            "confidence": round(ml_prob, 2),
            "reason": reason
        }

class AIExplanationService(AIAgentBase):
    def get_merchant_explanation(
        self,
        transaction_id: str,
        failure_code: str,
        ml_prob: float,
        recommended_action: str,
        reason: str
    ) -> str:
        """Generate human-readable justification for the recovery action."""
        if self.use_mock:
            mode_prefix = "[DEMO AI] "
            return f"{mode_prefix}RecoverAI analyzed transaction {transaction_id} which failed due to '{failure_code}'. Our ML model predicted a {int(ml_prob*100)}% recovery chance. Decided to trigger '{recommended_action}' because: {reason}."
            
        # Live Gemini explanation
        prompt = f"""
        Explain to a merchant why RecoverAI chose the recovery strategy '{recommended_action}' for a failed transaction.
        Transaction ID: {transaction_id}
        Failure Code: {failure_code}
        ML Recovery Probability: {ml_prob * 100}%
        Core Decision Reason: {reason}
        
        Write a concise, professional 2-3 sentence explanation.
        """
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                resp_json = response.json()
                explanation = resp_json['candidates'][0]['content']['parts'][0]['text']
                return explanation.strip()
        except Exception as e:
            print(f"Error calling Gemini for explanation: {e}")
            
        return f"RecoverAI analyzed transaction {transaction_id} (Failure: {failure_code}). Recommended: {recommended_action}. Reason: {reason}."
