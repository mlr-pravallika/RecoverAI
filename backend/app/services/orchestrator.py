import json
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.models import models
from backend.app.ml.classifier import predict_recovery_probability
from backend.app.services.ai_service import RootCauseAgent, RevenueRiskAgent, RecoveryDecisionAgent, AIExplanationService
from backend.app.policies.engine import PolicyEngine

VALID_TRANSITIONS = {
    "FAILED": ["ANALYZING"],
    "ANALYZING": ["RECOVERY_ELIGIBLE", "ACTION_PENDING", "MANUAL_REVIEW", "STOPPED"],
    "RECOVERY_ELIGIBLE": ["ACTION_PENDING", "STOPPED", "MANUAL_REVIEW"],
    "ACTION_PENDING": ["ACTION_EXECUTED", "MANUAL_REVIEW", "STOPPED"],
    "ACTION_EXECUTED": ["AWAITING_RESULT", "RECOVERED", "STOPPED", "MANUAL_REVIEW"],
    "AWAITING_RESULT": ["RECOVERED", "STOPPED", "ACTION_PENDING", "MANUAL_REVIEW"],
    "RECOVERED": [],
    "MANUAL_REVIEW": ["ACTION_PENDING", "STOPPED", "RECOVERED"],
    "STOPPED": []
}

class OrchestratorError(Exception):
    pass

class RecoveryOrchestrator:
    @staticmethod
    def transition_state(
        db: Session,
        case: models.RecoveryCase,
        new_state: str,
        actor: str,
        reason: str,
        metadata: dict = None
    ) -> models.RecoveryCase:
        old_state = case.status
        
        # Validate state transition
        allowed_next_states = VALID_TRANSITIONS.get(old_state, [])
        if new_state not in allowed_next_states:
            raise OrchestratorError(
                f"Invalid state transition from '{old_state}' to '{new_state}' for case {case.id}."
            )
            
        # Update case status
        case.status = new_state
        case.updated_at = datetime.utcnow()
        
        # Log to audit trail
        audit_entry = models.AuditLog(
            transaction_id=case.transaction_id,
            recovery_case_id=case.id,
            timestamp=datetime.utcnow(),
            actor=actor,
            action="STATE_TRANSITION",
            previous_state=old_state,
            new_state=new_state,
            reason=reason,
            metadata_json=json.dumps(metadata) if metadata else None
        )
        db.add(audit_entry)
        db.commit()
        return case

    @classmethod
    def initiate_recovery(cls, db: Session, transaction_id: str) -> models.RecoveryCase:
        """Triggered upon receiving a payment failure signal."""
        # 1. Verify transaction exists and is failed
        tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
        if not tx:
            raise OrchestratorError(f"Transaction {transaction_id} not found.")
        if tx.status != "failed":
            raise OrchestratorError(f"Transaction {transaction_id} is not in failed status.")
            
        # 2. Check if a recovery case already exists for this transaction
        existing_case = db.query(models.RecoveryCase).filter(
            models.RecoveryCase.transaction_id == transaction_id
        ).first()
        if existing_case:
            return existing_case
            
        # 3. Create initial recovery case in FAILED state
        case = models.RecoveryCase(
            transaction_id=transaction_id,
            status="FAILED",
            retry_count=0,
            max_retries=3,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        
        # 4. Transition immediately to ANALYZING
        return cls.transition_state(
            db=db,
            case=case,
            new_state="ANALYZING",
            actor="SYSTEM",
            reason="Payment failure detected. Initiating automated recovery analysis workflow.",
            metadata={"payment_method": tx.payment_method, "failure_code": tx.failure_code}
        )

    @classmethod
    def run_analysis_and_decide(cls, db: Session, case_id: int) -> dict:
        """Runs the classifier, AI reasoning agents, policy engine, and moves state."""
        case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
        if not case:
            raise OrchestratorError(f"Recovery case {case_id} not found.")
        if case.status != "ANALYZING":
            raise OrchestratorError(f"Recovery case {case_id} is not in ANALYZING state (current: {case.status}).")
            
        tx = db.query(models.Transaction).filter(models.Transaction.id == case.transaction_id).first()
        
        # 1. Run ML Model to get probability
        ml_prob = predict_recovery_probability(
            db=db,
            amount=tx.amount,
            payment_method=tx.payment_method,
            failure_code=tx.failure_code,
            customer_id=tx.customer_id
        )
        
        # 2. Run AI Agents for diagnosis and decision proposals
        rc_agent = RootCauseAgent()
        rev_agent = RevenueRiskAgent()
        dec_agent = RecoveryDecisionAgent()
        expl_service = AIExplanationService()
        
        failure_analysis = rc_agent.analyze_failure(tx.failure_code, tx.payment_method, "")
        risk_analysis = rev_agent.assess_risk(tx.amount, tx.customer_id, db)
        ai_proposal = dec_agent.make_decision(
            amount=tx.amount,
            root_cause=failure_analysis["classification"],
            ml_prob=ml_prob,
            priority=risk_analysis["recovery_priority"],
            retry_count=case.retry_count
        )
        
        proposed_action = ai_proposal["recommended_action"]
        ai_reason = ai_proposal["reason"]
        
        # 3. Evaluate proposal via compliance policy guardrails
        policy_engine = PolicyEngine(db)
        policy_result = policy_engine.evaluate(
            transaction=tx,
            recovery_case=case,
            proposed_action=proposed_action,
            ai_confidence=ml_prob,
            root_cause_classification=failure_analysis["classification"]
        )
        
        final_action = policy_result["action"]
        policy_reason = policy_result["reason"]
        
        # Update case metadata
        case.recovery_probability = ml_prob
        case.expected_recovery = round(tx.amount * ml_prob, 2)
        case.recommended_action = final_action
        
        # 4. State transition based on policy output
        actor = "POLICY"
        metadata = {
            "ml_probability": ml_prob,
            "ai_proposed_action": proposed_action,
            "policy_action": final_action,
            "policy_rule_matched": policy_result["policy_checked"]
        }
        
        if final_action == "STOP":
            cls.transition_state(
                db=db,
                case=case,
                new_state="STOPPED",
                actor=actor,
                reason=f"Recovery stopped by policy engine. Reason: {policy_reason}",
                metadata=metadata
            )
        elif final_action == "MANUAL_REVIEW":
            cls.transition_state(
                db=db,
                case=case,
                new_state="MANUAL_REVIEW",
                actor=actor,
                reason=f"Escalated to human-in-the-loop review by policy engine. Reason: {policy_reason}",
                metadata=metadata
            )
        else: # RETRY or PAYMENT_LINK
            # Move to ACTION_PENDING
            cls.transition_state(
                db=db,
                case=case,
                new_state="ACTION_PENDING",
                actor=actor,
                reason=f"Recovery action '{final_action}' approved by policy engine. Reason: {policy_reason}",
                metadata=metadata
            )
            
        # Log explanation as an audit note or details
        explanation = expl_service.get_merchant_explanation(
            transaction_id=tx.id,
            failure_code=tx.failure_code,
            ml_prob=ml_prob,
            recommended_action=final_action,
            reason=ai_reason
        )
        
        # Save explanation to case metadata
        case.updated_at = datetime.utcnow()
        db.commit()
        
        # Add explanation entry to audit log
        db.add(models.AuditLog(
            transaction_id=tx.id,
            recovery_case_id=case.id,
            timestamp=datetime.utcnow(),
            actor="AI",
            action="EXPLAIN_DECISION",
            previous_state=None,
            new_state=None,
            reason=explanation,
            metadata_json=None
        ))
        db.commit()
        
        return {
            "case_id": case.id,
            "ml_probability": ml_prob,
            "ai_proposal": proposed_action,
            "policy_decision": final_action,
            "explanation": explanation
        }

    @classmethod
    def execute_action(cls, db: Session, case_id: int) -> dict:
        """Initiates execution of RETRY or PAYMENT_LINK and moves state to ACTION_EXECUTED -> AWAITING_RESULT."""
        case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
        if not case:
            raise OrchestratorError(f"Recovery case {case_id} not found.")
        if case.status != "ACTION_PENDING":
            raise OrchestratorError(f"Recovery case is not in ACTION_PENDING state (current: {case.status}).")
            
        action_type = case.recommended_action
        
        # 1. Create a RecoveryAction record
        db_action = models.RecoveryAction(
            recovery_case_id=case.id,
            action_type=action_type,
            status="PENDING",
            created_at=datetime.utcnow()
        )
        db.add(db_action)
        db.commit()
        db.refresh(db_action)
        
        # Increment retry count if it is a RETRY
        if action_type == "RETRY":
            case.retry_count += 1
            
        # 2. Transition state to ACTION_EXECUTED
        cls.transition_state(
            db=db,
            case=case,
            new_state="ACTION_EXECUTED",
            actor="SYSTEM",
            reason=f"Initiating execution of recovery action: {action_type}.",
            metadata={"action_id": db_action.id, "action_type": action_type}
        )
        
        # Perform action integration logic (simulated or real)
        db_action.status = "EXECUTED"
        db_action.details = f"Action {action_type} executed at {datetime.utcnow()}"
        db_action.updated_at = datetime.utcnow()
        db.commit()
        
        # 3. Transition immediately to AWAITING_RESULT
        cls.transition_state(
            db=db,
            case=case,
            new_state="AWAITING_RESULT",
            actor="SYSTEM",
            reason=f"Action executed. Awaiting payment event source verification.",
            metadata={"action_id": db_action.id}
        )
        
        return {
            "action_id": db_action.id,
            "status": "EXECUTED",
            "action_type": action_type
        }

    @classmethod
    def handle_payment_success(cls, db: Session, case_id: int, gateway_response: dict = None) -> models.RecoveryCase:
        """Triggered when payment succeeds. Transitions state to RECOVERED."""
        case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
        if not case:
            raise OrchestratorError(f"Recovery case {case_id} not found.")
            
        # Update original transaction status to captured
        tx = db.query(models.Transaction).filter(models.Transaction.id == case.transaction_id).first()
        tx.status = "captured"
        tx.updated_at = datetime.utcnow()
        
        # Transition to RECOVERED
        return cls.transition_state(
            db=db,
            case=case,
            new_state="RECOVERED",
            actor="SYSTEM",
            reason="Recovery successful. A payment event confirming full capture was validated.",
            metadata=gateway_response
        )

    @classmethod
    def handle_payment_failure(cls, db: Session, case_id: int, gateway_response: dict = None) -> models.RecoveryCase:
        """Triggered when retry or link payment fails. Decides whether to retry or stop."""
        case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
        if not case:
            raise OrchestratorError(f"Recovery case {case_id} not found.")
            
        policy_engine = PolicyEngine(db)
        tx = db.query(models.Transaction).filter(models.Transaction.id == case.transaction_id).first()
        
        # Check retry eligibility
        if case.retry_count >= policy_engine.config.max_retries:
            # STOP
            return cls.transition_state(
                db=db,
                case=case,
                new_state="STOPPED",
                actor="POLICY",
                reason=f"Recovery stopped. Max retry limit of {policy_engine.config.max_retries} attempts reached.",
                metadata=gateway_response
            )
        else:
            # Move back to ACTION_PENDING for next execution attempt
            return cls.transition_state(
                db=db,
                case=case,
                new_state="ACTION_PENDING",
                actor="SYSTEM",
                reason=f"Recovery payment attempt failed. Scheduling attempt #{case.retry_count + 1}.",
                metadata=gateway_response
            )
            
    @classmethod
    def cancel_recovery(cls, db: Session, case_id: int, reason: str) -> models.RecoveryCase:
        """Allows merchant to manually abort a recovery case."""
        case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
        if not case:
            raise OrchestratorError(f"Recovery case {case_id} not found.")
        if case.status in ["RECOVERED", "STOPPED"]:
            raise OrchestratorError(f"Cannot abort a case in terminal state '{case.status}'.")
            
        return cls.transition_state(
            db=db,
            case=case,
            new_state="STOPPED",
            actor="ADMIN",
            reason=f"Recovery aborted manually by merchant user. Reason: {reason}",
            metadata=None
        )
