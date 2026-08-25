from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from backend.app.models import models

class PolicyEngine:
    def __init__(self, db: Session):
        self.db = db
        # Load single-row policy config
        self.config = db.query(models.PolicyConfig).filter(models.PolicyConfig.id == 1).first()
        if not self.config:
            # Fallback default values if database entry is missing
            self.config = models.PolicyConfig(
                id=1,
                max_retries=3,
                min_confidence=0.70,
                recovery_window_hours=72,
                max_automated_amount=40000.0
            )

    def evaluate(
        self,
        transaction: models.Transaction,
        recovery_case: models.RecoveryCase,
        proposed_action: str,
        ai_confidence: float,
        root_cause_classification: str
    ) -> dict:
        """
        Evaluate the proposed action against deterministic compliance policy rules.
        Returns:
            {
                "allowed": bool,
                "action": str (RETRY, PAYMENT_LINK, MANUAL_REVIEW, STOP),
                "reason": str,
                "policy_checked": str
            }
        """
        # Rule 1: If transaction is already successful -> STOP
        if transaction.status == "captured":
            return {
                "allowed": False,
                "action": "STOP",
                "reason": "Transaction is already successful.",
                "policy_checked": "SUCCESS_CHECK"
            }

        # Rule 2: If fraud flag detected -> STOP
        if transaction.failure_type == "fraud" or root_cause_classification == "fraud_suspected":
            return {
                "allowed": False,
                "action": "STOP",
                "reason": "Compliance trigger: Suspicious fraudulent activity detected.",
                "policy_checked": "FRAUD_CHECK"
            }

        # Rule 3: If permanent failure (expired card, etc.) -> STOP
        if transaction.failure_type == "permanent" or root_cause_classification == "permanent_failure":
            return {
                "allowed": False,
                "action": "STOP",
                "reason": "Decline code indicates a permanent failure that cannot be retried.",
                "policy_checked": "PERMANENT_CHECK"
            }

        # Rule 4: If retry count exceeds MAX_RETRIES -> STOP
        if recovery_case.retry_count >= self.config.max_retries:
            return {
                "allowed": False,
                "action": "STOP",
                "reason": f"Maximum automated recovery retries ({self.config.max_retries}) exhausted.",
                "policy_checked": "RETRY_LIMIT_CHECK"
            }

        # Rule 5: If recovery window has expired -> STOP
        time_elapsed = datetime.utcnow() - recovery_case.created_at
        if time_elapsed > timedelta(hours=self.config.recovery_window_hours):
            return {
                "allowed": False,
                "action": "STOP",
                "reason": f"Recovery window of {self.config.recovery_window_hours} hours has expired.",
                "policy_checked": "WINDOW_EXPIRED_CHECK"
            }

        # Rule 6: If proposed action is STOP -> STOP
        if proposed_action == "STOP":
            return {
                "allowed": True,
                "action": "STOP",
                "reason": "AI engine recommended stopping recovery.",
                "policy_checked": "STOP_RULE"
            }

        # Rule 7: If transaction amount exceeds automated threshold -> MANUAL_REVIEW
        if transaction.amount > self.config.max_automated_amount:
            return {
                "allowed": False,
                "action": "MANUAL_REVIEW",
                "reason": f"Transaction amount of ₹{transaction.amount:,} exceeds the automated recovery limit of ₹{self.config.max_automated_amount:,}.",
                "policy_checked": "AMOUNT_LIMIT_CHECK"
            }

        # Rule 8: If AI confidence/recovery probability is below minimum -> MANUAL_REVIEW
        if ai_confidence < self.config.min_confidence:
            return {
                "allowed": False,
                "action": "MANUAL_REVIEW",
                "reason": f"Recovery confidence ({ai_confidence:.2f}) is below the required threshold of {self.config.min_confidence:.2f}.",
                "policy_checked": "CONFIDENCE_CHECK"
            }

        # If everything passes, ALLOW the action
        return {
            "allowed": True,
            "action": proposed_action,
            "reason": f"Proposed recovery action '{proposed_action}' matches compliance rules.",
            "policy_checked": "ALL_RULES_PASSED"
        }
