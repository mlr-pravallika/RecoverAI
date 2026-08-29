import os
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from google import genai

from backend.app.core.config import settings
from backend.app.models import models
from backend.app.ml.classifier import predict_recovery_probability

class AIAgentBase:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.use_mock = not bool(self.api_key and self.api_key.strip())
        self.client = None
        
        if self.use_mock:
            print("GEMINI_API_KEY not found. Running AI Agents in MOCK / DEMO mode.")
        else:
            print("GEMINI_API_KEY found. Running AI Agents in GEMINI LIVE mode.")
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize GenAI client: {e}. Falling back to MOCK mode.")
                self.use_mock = True

    def _call_gemini(self, prompt: str, enforce_json: bool = True) -> Optional[str]:
        if self.use_mock or not self.client:
            return None
            
        try:
            config = {}
            if enforce_json:
                config = {"response_mime_type": "application/json"}
                
            from backend.app.services.gemini_service import GeminiService
            active_model = GeminiService.get_active_model() or "gemini-2.5-flash"
            response = self.client.models.generate_content(
                model=active_model,
                contents=prompt,
                config=config
            )
            
            if response and response.text:
                return response.text.strip()
            return None
        except Exception as e:
            print(f"Error calling Gemini via GenAI SDK: {e}. Falling back to mock data.")
            return None

class RootCauseAgent(AIAgentBase):
    def analyze_failure(self, failure_code: str, payment_method: str, attempt_details: str) -> Dict[str, Any]:
        """Classify failure root cause: temporary_failure, permanent_failure, or fraud_suspected."""
        mock_result = {
            "classification": "temporary_failure",
            "confidence": 0.85,
            "root_cause": "Temporary network timeout or banking server drop."
        }
        
        if failure_code == "BAD_REQUEST_PAYMENT_RISK_THRESHOLD_EXCEEDED":
            mock_result = {
                "classification": "fraud_suspected",
                "confidence": 0.98,
                "root_cause": "Razorpay risk rules flagged the payment card as suspicious."
            }
        elif failure_code == "BAD_REQUEST_PAYMENT_CARD_EXPIRED":
            mock_result = {
                "classification": "permanent_failure",
                "confidence": 0.95,
                "root_cause": "The customer's card is expired and cannot be retried."
            }
        elif failure_code == "GATEWAY_ERROR":
            mock_result = {
                "classification": "temporary_failure",
                "confidence": 0.92,
                "root_cause": "Network gateway timeout between Razorpay and the issuing bank."
            }

        if self.use_mock:
            return mock_result

        # Live Gemini call using official SDK
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
        
        raw_text = self._call_gemini(prompt, enforce_json=True)
        if raw_text:
            try:
                parsed = json.loads(raw_text)
                if "classification" in parsed:
                    return parsed
            except Exception:
                pass
                
        return mock_result

class RevenueRiskAgent(AIAgentBase):
    def assess_risk(self, amount: float, customer_id: str, db: Session) -> Dict[str, Any]:
        """Assess the priority of recovery based on transaction volume, history, and customer value."""
        customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
        history_txs = db.query(models.Transaction).filter(models.Transaction.customer_id == customer_id).all()
        total_spent = sum(t.amount for t in history_txs if t.status == "captured")
        success_count = sum(1 for t in history_txs if t.status == "captured")
        
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

        # Select action based on ML probability & transaction size
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
        mock_explanation = f"[DEMO AI] RecoverAI analyzed transaction {transaction_id} which failed due to '{failure_code}'. Our ML model predicted a {int(ml_prob*100)}% recovery chance. Decided to trigger '{recommended_action}' because: {reason}."
        
        if self.use_mock:
            return mock_explanation

        # Live Gemini explanation using SDK
        prompt = f"""
        Explain to a merchant why RecoverAI chose the recovery strategy '{recommended_action}' for a failed transaction.
        Transaction ID: {transaction_id}
        Failure Code: {failure_code}
        ML Recovery Probability: {ml_prob * 100}%
        Core Decision Reason: {reason}
        
        Write a concise, professional 2-3 sentence explanation.
        """
        
        raw_text = self._call_gemini(prompt, enforce_json=False)
        if raw_text:
            return raw_text
            
        return f"RecoverAI analyzed transaction {transaction_id} (Failure: {failure_code}). Recommended: {recommended_action}. Reason: {reason}."
