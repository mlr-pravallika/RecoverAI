import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.models import models
from backend.app.schemas import schemas
from backend.app.services.orchestrator import RecoveryOrchestrator
from backend.app.policies.engine import PolicyEngine

class SimulationEngine:
    @staticmethod
    def run_batch_simulation(db: Session, num_transactions: int, preset: str) -> dict:
        """
        Runs the state machine recovery flow across a subset of failed transactions.
        Simulates outcomes based on recovery probabilities.
        """
        # Load failed transactions
        failed_txs = db.query(models.Transaction).filter(
            models.Transaction.status == "failed"
        ).order_by(models.Transaction.created_at.desc()).limit(num_transactions).all()
        
        # Ensure we have active recovery cases for them
        cases = []
        for tx in failed_txs:
            case = db.query(models.RecoveryCase).filter(
                models.RecoveryCase.transaction_id == tx.id
            ).first()
            if not case:
                case = RecoveryOrchestrator.initiate_recovery(db, tx.id)
            
            # Reset active cases to ANALYZING for simulation run
            if case.status in ["RECOVERED", "STOPPED", "MANUAL_REVIEW"]:
                # Force reset for simulation purposes
                case.status = "ANALYZING"
                case.retry_count = 0
                db.commit()
            cases.append(case)
            
        # Temporarily apply preset policy config
        original_config = db.query(models.PolicyConfig).filter(models.PolicyConfig.id == 1).first()
        temp_max_retries = 3
        temp_min_confidence = 0.70
        temp_max_amount = 40000.0
        
        if preset == "conservative":
            temp_min_confidence = 0.85
            temp_max_amount = 15000.0
        elif preset == "aggressive":
            temp_min_confidence = 0.50
            temp_max_amount = 100000.0
            temp_max_retries = 5

        # Save current config to restore later
        orig_max_retries = original_config.max_retries if original_config else 3
        orig_min_confidence = original_config.min_confidence if original_config else 0.70
        orig_max_amount = original_config.max_automated_amount if original_config else 40000.0
        
        if original_config:
            original_config.max_retries = temp_max_retries
            original_config.min_confidence = temp_min_confidence
            original_config.max_automated_amount = temp_max_amount
            db.commit()

        # Metrics trackers
        analyzed = len(cases)
        revenue_at_risk = sum(tx.amount for tx in failed_txs)
        recoverable_count = 0
        actions_executed = 0
        recovered_revenue = 0.0
        manual_escalations = 0
        blocked_actions = 0
        
        strategy_dist = {"RETRY": 0, "PAYMENT_LINK": 0, "STOP": 0, "MANUAL_REVIEW": 0}
        failure_dist = {}

        try:
            for case in cases:
                tx = db.query(models.Transaction).filter(models.Transaction.id == case.transaction_id).first()
                
                # Keep track of failure code distribution
                failure_dist[tx.failure_code] = failure_dist.get(tx.failure_code, 0) + 1
                
                # 1. Run analysis & decision
                analysis_res = RecoveryOrchestrator.run_analysis_and_decide(db, case.id)
                policy_dec = analysis_res["policy_decision"]
                ml_prob = analysis_res["ml_probability"]
                
                strategy_dist[policy_dec] = strategy_dist.get(policy_dec, 0) + 1
                
                if policy_dec == "STOP":
                    blocked_actions += 1
                elif policy_dec == "MANUAL_REVIEW":
                    manual_escalations += 1
                else: # RETRY or PAYMENT_LINK
                    recoverable_count += 1
                    actions_executed += 1
                    
                    # Execute action
                    exec_res = RecoveryOrchestrator.execute_action(db, case.id)
                    
                    # Simulate outcome based on ML probability
                    outcome_success = random.random() < ml_prob
                    if outcome_success:
                        RecoveryOrchestrator.handle_payment_success(db, case.id, {"simulated": True})
                        recovered_revenue += tx.amount
                    else:
                        RecoveryOrchestrator.handle_payment_failure(db, case.id, {"simulated": True})
                        # Retry if applicable
                        if case.status == "ACTION_PENDING":
                            # Simulate 2nd attempt
                            actions_executed += 1
                            exec_res = RecoveryOrchestrator.execute_action(db, case.id)
                            outcome_success_2 = random.random() < ml_prob
                            if outcome_success_2:
                                RecoveryOrchestrator.handle_payment_success(db, case.id, {"simulated": True})
                                recovered_revenue += tx.amount
                            else:
                                RecoveryOrchestrator.handle_payment_failure(db, case.id, {"simulated": True})
            
            # Log audit for simulation run
            db.add(models.AuditLog(
                actor="SYSTEM",
                action="BATCH_SIMULATION_RUN",
                reason=f"Executed recovery simulation across {analyzed} cases with '{preset}' policy.",
                metadata_json=f'{{"preset": "{preset}", "recovered": {recovered_revenue}}}',
                timestamp=datetime.utcnow()
            ))
            db.commit()

        finally:
            # Restore original policy configurations
            if original_config:
                original_config.max_retries = orig_max_retries
                original_config.min_confidence = orig_min_confidence
                original_config.max_automated_amount = orig_max_amount
                db.commit()

        return {
            "run_id": str(uuid.uuid4())[:8],
            "transactions_analyzed": analyzed,
            "revenue_at_risk": round(revenue_at_risk, 2),
            "recoverable_transactions": recoverable_count,
            "actions_executed": actions_executed,
            "recovered_revenue": round(recovered_revenue, 2),
            "recovery_rate": round((recovered_revenue / revenue_at_risk * 100) if revenue_at_risk > 0 else 0.0, 2),
            "manual_escalations": manual_escalations,
            "unsafe_actions_prevented": blocked_actions,
            "strategy_distribution": strategy_dist,
            "failure_distribution": failure_dist
        }

    @staticmethod
    def calculate_what_if(db: Session, config: schemas.WhatIfRequest) -> dict:
        """
        Calculates theoretical performance stats on the seeded transaction log
        under different policy configs (without writing modifications to database).
        """
        # Load all failed transactions
        failed_txs = db.query(models.Transaction).filter(models.Transaction.status == "failed").all()
        total_failed_revenue = sum(t.amount for t in failed_txs)
        
        # We need cases to evaluate
        cases = db.query(models.RecoveryCase).all()
        cases_by_tx = {c.transaction_id: c for c in cases}
        
        def run_eval_for_policy(max_retries, min_confidence, max_automated_amount):
            recovered = 0.0
            manual = 0
            blocked = 0
            
            # Simple simulation logic for each failed transaction
            for tx in failed_txs:
                case = cases_by_tx.get(tx.id)
                prob = case.recovery_probability if case else 0.50
                
                # Check fraud / permanent decline
                is_blocked = (tx.failure_type == "fraud" or tx.failure_type == "permanent")
                
                if is_blocked:
                    blocked += 1
                elif tx.amount > max_automated_amount:
                    manual += 1
                elif prob < min_confidence:
                    manual += 1
                else:
                    # Successful recovery simulation based on probability
                    # To be deterministic for What-If, we can use probability directly:
                    # recovered revenue = amount * probability
                    recovered += tx.amount * prob
                    
            rec_rate = (recovered / total_failed_revenue * 100) if total_failed_revenue > 0 else 0.0
            man_rate = (manual / len(failed_txs) * 100) if failed_txs else 0.0
            
            return {
                "max_retries": max_retries,
                "min_confidence": min_confidence,
                "max_automated_amount": max_automated_amount,
                "recovery_rate": round(rec_rate, 2),
                "recovered_revenue": round(recovered, 2),
                "manual_review_rate": round(man_rate, 2),
                "blocked_actions_count": blocked
            }

        current = run_eval_for_policy(config.max_retries, config.min_confidence, config.max_automated_amount)
        current["preset_name"] = "Custom Configuration"
        
        conservative = run_eval_for_policy(3, 0.85, 15000.0)
        conservative["preset_name"] = "Conservative"
        
        balanced = run_eval_for_policy(3, 0.70, 40000.0)
        balanced["preset_name"] = "Balanced"
        
        aggressive = run_eval_for_policy(5, 0.50, 100000.0)
        aggressive["preset_name"] = "Aggressive"
        
        explanation = (
            f"Applying {config.min_confidence*100}% confidence threshold and limit of ₹{config.max_automated_amount:,} "
            f"secures ₹{current['recovered_revenue']:,} in expected recovered revenue. "
            f"Increasing confidence reduces manual outreach but increases the rate of unrecovered checkouts."
        )
        
        return {
            "current": current,
            "presets": [conservative, balanced, aggressive],
            "explanation": explanation
        }

    @staticmethod
    def trigger_demo_scenario(db: Session, scenario: str, merchant_id: str) -> dict:
        """
        Creates a custom mock failed transaction and initiates recovery
        based on the requested scenario (Cases A through I).
        """
        scenarios = {
            "CASE_A": {
                "code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                "method": "upi",
                "amount": 2500.0,
                "desc": "Temporary failure -> Retry -> Success"
            },
            "CASE_C": {
                "code": "BAD_REQUEST_PAYMENT_CARD_EXPIRED",
                "method": "card",
                "amount": 1500.0,
                "desc": "Permanent failure -> STOP"
            },
            "CASE_D": {
                "code": "BAD_REQUEST_PAYMENT_RISK_THRESHOLD_EXCEEDED",
                "method": "card",
                "amount": 35000.0,
                "desc": "Fraud flag -> STOP"
            },
            "CASE_E": {
                "code": "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK",
                "method": "netbanking",
                "amount": 45000.0,
                "desc": "Low confidence / High value -> MANUAL REVIEW"
            },
            "CASE_F": {
                "code": "BAD_REQUEST_PAYMENT_CANCELLED_BY_USER",
                "method": "upi",
                "amount": 12000.0,
                "desc": "Payment Link -> payment -> RECOVERED"
            }
        }
        
        scen_info = scenarios.get(scenario, scenarios["CASE_A"])
        
        # Pick a customer for this merchant
        cust = db.query(models.Customer).filter(models.Customer.merchant_id == merchant_id).first()
        if not cust:
            # Create a customer
            cust = models.Customer(
                id=f"cust_demo_{random.randint(1000, 9999)}",
                merchant_id=merchant_id,
                name="Demo Customer",
                email="demo@recoverai.com"
            )
            db.add(cust)
            db.commit()
            
        tx_id = f"pay_demo_{scenario.lower()}_{random.randint(1000, 9999)}"
        tx = models.Transaction(
            id=tx_id,
            merchant_id=merchant_id,
            customer_id=cust.id,
            amount=scen_info["amount"],
            currency="INR",
            status="failed",
            payment_method=scen_info["method"],
            failure_code=scen_info["code"],
            failure_type="fraud" if scen_info["code"] == "BAD_REQUEST_PAYMENT_RISK_THRESHOLD_EXCEEDED" else "permanent" if scen_info["code"] == "BAD_REQUEST_PAYMENT_CARD_EXPIRED" else "temporary",
            is_demo=True,
            created_at=datetime.utcnow()
        )
        db.add(tx)
        
        attempt = models.PaymentAttempt(
            id=f"att_demo_{random.randint(10000, 99999)}",
            transaction_id=tx_id,
            attempt_number=1,
            payment_method=scen_info["method"],
            failure_code=scen_info["code"],
            status="failed",
            created_at=datetime.utcnow()
        )
        db.add(attempt)
        db.commit()
        
        # Initiate recovery orchestrator
        case = RecoveryOrchestrator.initiate_recovery(db, tx_id)
        analysis_res = RecoveryOrchestrator.run_analysis_and_decide(db, case.id)
        
        return {
            "transaction_id": tx_id,
            "case_id": case.id,
            "scenario": scenario,
            "description": scen_info["desc"],
            "analysis": analysis_res
        }

    @staticmethod
    def seed_merchant_demo_data(db: Session, merchant_id: str):
        """
        Clones the global unassociated seeded dataset for a newly registered merchant
        to populate their Demo Mode data instantly.
        """
        # Find global customers (where merchant_id is None or empty)
        global_customers = db.query(models.Customer).filter(
            (models.Customer.merchant_id == None) | (models.Customer.merchant_id == "")
        ).all()
        
        customer_map = {}
        for cust in global_customers:
            new_cust_id = f"{cust.id}_{merchant_id[:6]}"
            # Prevent duplicate key if re-run
            existing = db.query(models.Customer).filter(models.Customer.id == new_cust_id).first()
            if not existing:
                new_cust = models.Customer(
                    id=new_cust_id,
                    merchant_id=merchant_id,
                    name=cust.name,
                    email=cust.email,
                    phone=cust.phone,
                    created_at=cust.created_at
                )
                db.add(new_cust)
                customer_map[cust.id] = new_cust_id
            else:
                customer_map[cust.id] = existing.id
                
        db.commit() # Flush so customer IDs exist
        
        # Find global transactions
        global_txs = db.query(models.Transaction).filter(
            (models.Transaction.merchant_id == None) | (models.Transaction.merchant_id == "")
        ).all()
        
        for tx in global_txs:
            new_tx_id = f"{tx.id}_{merchant_id[:6]}"
            existing_tx = db.query(models.Transaction).filter(models.Transaction.id == new_tx_id).first()
            if existing_tx:
                continue
                
            new_tx = models.Transaction(
                id=new_tx_id,
                merchant_id=merchant_id,
                customer_id=customer_map.get(tx.customer_id, tx.customer_id),
                order_id=tx.order_id,
                amount=tx.amount,
                currency=tx.currency,
                status=tx.status,
                payment_method=tx.payment_method,
                failure_code=tx.failure_code,
                failure_type=tx.failure_type,
                is_demo=True,
                created_at=tx.created_at,
                updated_at=tx.updated_at
            )
            db.add(new_tx)
            
            # payment attempts
            for attempt in tx.attempts:
                new_att_id = f"{attempt.id}_{merchant_id[:6]}"
                new_att = models.PaymentAttempt(
                    id=new_att_id,
                    transaction_id=new_tx_id,
                    attempt_number=attempt.attempt_number,
                    payment_method=attempt.payment_method,
                    failure_code=attempt.failure_code,
                    failure_reason=attempt.failure_reason,
                    status=attempt.status,
                    created_at=attempt.created_at
                )
                db.add(new_att)
                
            # recovery cases
            for case in tx.recovery_cases:
                new_case = models.RecoveryCase(
                    merchant_id=merchant_id,
                    transaction_id=new_tx_id,
                    status=case.status,
                    recovery_probability=case.recovery_probability,
                    expected_recovery=case.expected_recovery,
                    recommended_action=case.recommended_action,
                    retry_count=case.retry_count,
                    max_retries=case.max_retries,
                    created_at=case.created_at,
                    updated_at=case.updated_at
                )
                db.add(new_case)
                db.flush() # get new_case.id
                
                # recovery actions
                for action in case.actions:
                    new_act = models.RecoveryAction(
                        recovery_case_id=new_case.id,
                        action_type=action.action_type,
                        status=action.status,
                        details=action.details,
                        created_at=action.created_at,
                        updated_at=action.updated_at
                    )
                    db.add(new_act)
                    
                # audit logs
                audit_logs = db.query(models.AuditLog).filter(models.AuditLog.recovery_case_id == case.id).all()
                for audit in audit_logs:
                    new_audit = models.AuditLog(
                        merchant_id=merchant_id,
                        transaction_id=new_tx_id,
                        recovery_case_id=new_case.id,
                        timestamp=audit.timestamp,
                        actor=audit.actor,
                        action=audit.action,
                        previous_state=audit.previous_state,
                        new_state=audit.new_state,
                        reason=audit.reason,
                        metadata_json=audit.metadata_json
                    )
                    db.add(new_audit)
                    
        db.commit()

