import sys
import os
import random
from datetime import datetime, timedelta

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal, engine, Base
from backend.app.models.models import Customer, Transaction, PaymentAttempt, RecoveryCase, RecoveryAction, AuditLog, PolicyConfig

# Failure configurations
FAILURE_CONFIGS = [
    {
        "code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
        "type": "temporary",
        "method_prob": {"card": 0.3, "upi": 0.5, "netbanking": 0.1, "wallet": 0.1},
        "base_prob": 0.85,
        "reason": "Customer timed out during authentication redirect."
    },
    {
        "code": "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK",
        "type": "temporary",
        "method_prob": {"card": 0.5, "upi": 0.2, "netbanking": 0.2, "wallet": 0.1},
        "base_prob": 0.55,
        "reason": "Insufficient funds or temporary bank server downtime."
    },
    {
        "code": "BAD_REQUEST_PAYMENT_CANCELLED_BY_USER",
        "type": "temporary",
        "method_prob": {"card": 0.2, "upi": 0.6, "netbanking": 0.1, "wallet": 0.1},
        "base_prob": 0.70,
        "reason": "Checkout modal closed by the customer before entering credentials."
    },
    {
        "code": "BAD_REQUEST_PAYMENT_AUTHENTICATION_FAILED",
        "type": "temporary",
        "method_prob": {"card": 0.6, "upi": 0.2, "netbanking": 0.1, "wallet": 0.1},
        "base_prob": 0.75,
        "reason": "Incorrect OTP or 3D secure pin verification failure."
    },
    {
        "code": "GATEWAY_ERROR",
        "type": "temporary",
        "method_prob": {"card": 0.4, "upi": 0.3, "netbanking": 0.2, "wallet": 0.1},
        "base_prob": 0.90,
        "reason": "Network link failure between PSP gateway and card network."
    },
    {
        "code": "BAD_REQUEST_PAYMENT_CARD_EXPIRED",
        "type": "permanent",
        "method_prob": {"card": 1.0, "upi": 0.0, "netbanking": 0.0, "wallet": 0.0},
        "base_prob": 0.05,
        "reason": "The card expiry date has passed. Alternative card required."
    },
    {
        "code": "BAD_REQUEST_PAYMENT_RISK_THRESHOLD_EXCEEDED",
        "type": "fraud",
        "method_prob": {"card": 0.8, "upi": 0.1, "netbanking": 0.1, "wallet": 0.0},
        "base_prob": 0.00,
        "reason": "High fraud score. Action blocked by compliance engine."
    }
]

FIRST_NAMES = ["Rahul", "Priya", "Amit", "Sneha", "Anil", "Deepa", "Vikram", "Neha", "Sanjay", "Kiran", "Rohan", "Anjali", "Sunil", "Ritu", "Vivek"]
LAST_NAMES = ["Sharma", "Verma", "Patel", "Gupta", "Mehta", "Singh", "Joshi", "Rao", "Nair", "Reddy", "Choudhury", "Das", "Sen", "Kumar", "Iyer"]
DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com"]

def generate_customer_pool(num_customers=150):
    customers = []
    for i in range(num_customers):
        c_id = f"cust_{random.randint(100000, 999999)}"
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{random.randint(10,99)}@{random.choice(DOMAINS)}"
        phone = f"+91{random.randint(7000000000, 9999999999)}"
        customers.append({
            "id": c_id,
            "name": name,
            "email": email,
            "phone": phone
        })
    return customers

def get_recommended_action(prob, amount, fraud):
    if fraud:
        return "STOP"
    if prob < 0.2:
        return "STOP"
    elif prob < 0.7:
        if amount > 15000:
            return "MANUAL_REVIEW"
        return "PAYMENT_LINK"
    else:
        if amount > 30000:
            return "MANUAL_REVIEW"
        return "RETRY"

def populate_data():
    # Initialize DB tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Clear existing data
        print("Clearing database...")
        db.query(AuditLog).delete()
        db.query(RecoveryAction).delete()
        db.query(RecoveryCase).delete()
        db.query(PaymentAttempt).delete()
        db.query(Transaction).delete()
        db.query(Customer).delete()
        db.query(PolicyConfig).delete()
        db.commit()
        
        # Add default policy config
        default_policy = PolicyConfig(
            id=1,
            max_retries=3,
            min_confidence=0.70,
            recovery_window_hours=72,
            max_automated_amount=40000.0
        )
        db.add(default_policy)
        
        print("Generating customer pool...")
        customers_data = generate_customer_pool(150)
        customer_objs = []
        for c in customers_data:
            cust = Customer(id=c["id"], name=c["name"], email=c["email"], phone=c["phone"])
            db.add(cust)
            customer_objs.append(cust)
        db.commit()
        
        print("Generating 1000 transactions...")
        # Keep track of customer histories in memory to generate meaningful patterns
        # customer_id -> (success_count, failure_count, retry_success_count)
        history = {c.id: [0, 0, 0] for c in customer_objs}
        
        # Generate timestamps over the last 30 days
        base_time = datetime.utcnow() - timedelta(days=30)
        
        transactions_to_add = []
        
        for idx in range(1000):
            tx_id = f"pay_{random.randint(100000000, 999999999)}"
            order_id = f"order_{random.randint(100000000, 999999999)}"
            
            cust = random.choice(customer_objs)
            c_hist = history[cust.id]
            
            # Select amount with lognormal-like distribution (more small, fewer large)
            amount = round(random.lognormvariate(7.5, 1.2), 2)
            if amount < 100:
                amount = round(random.randint(100, 500) + random.random(), 2)
            elif amount > 75000:
                amount = round(random.randint(50000, 75000) + random.random(), 2)
                
            payment_method = random.choice(["card", "upi", "netbanking", "wallet"])
            
            # 40% initial success rate, 60% failures to focus on recovery workflow
            is_success = random.random() < 0.40
            
            # Subscription flag - recurring billing (approx 15% of transactions)
            subscription_flag = random.random() < 0.15
            
            # Timestamps spread out sequentially
            tx_time = base_time + timedelta(minutes=random.randint(1, 40) * idx)
            
            if is_success:
                status = "captured"
                failure_code = None
                failure_type = None
                fraud_flag = False
                
                # Update history
                c_hist[0] += 1
            else:
                status = "failed"
                # Select a failure config
                config = random.choice(FAILURE_CONFIGS)
                failure_code = config["code"]
                failure_type = config["type"]
                fraud_flag = (failure_type == "fraud")
                
                # Override payment method based on probabilities of failure
                method_weights = [config["method_prob"][m] for m in ["card", "upi", "netbanking", "wallet"]]
                payment_method = random.choices(["card", "upi", "netbanking", "wallet"], weights=method_weights, k=1)[0]
                
                # Update history
                c_hist[1] += 1
            
            tx = Transaction(
                id=tx_id,
                customer_id=cust.id,
                order_id=order_id,
                amount=amount,
                currency="INR",
                status=status,
                payment_method=payment_method,
                failure_code=failure_code,
                failure_type=failure_type,
                created_at=tx_time,
                updated_at=tx_time
            )
            db.add(tx)
            
            # Save historical state *before* this transaction for ML feature purposes
            # We'll store it inside the recovery cases or process attempts
            
            # Create payment attempt
            attempt = PaymentAttempt(
                id=f"att_{random.randint(1000000, 9999999)}",
                transaction_id=tx_id,
                attempt_number=1,
                payment_method=payment_method,
                failure_code=failure_code,
                failure_reason=next((f["reason"] for f in FAILURE_CONFIGS if f["code"] == failure_code), None) if not is_success else None,
                status="captured" if is_success else "failed",
                created_at=tx_time
            )
            db.add(attempt)
            
            # If failed, let's create a RecoveryCase
            if not is_success:
                # Heuristic calculation for recovery probability
                if fraud_flag:
                    prob = 0.0
                elif failure_code == "BAD_REQUEST_PAYMENT_CARD_EXPIRED":
                    prob = 0.05
                elif failure_code == "GATEWAY_ERROR":
                    prob = 0.90
                else:
                    # History factor: successful retries and successes boost probability
                    hist_total = c_hist[0] + c_hist[1] + c_hist[2]
                    if hist_total > 0:
                        prob = round((c_hist[0] + c_hist[2] + 1) / (hist_total + 2), 2)
                    else:
                        prob = 0.50
                    # Add noise
                    prob = max(0.1, min(0.95, prob + random.uniform(-0.1, 0.1)))
                
                prob = round(prob, 2)
                expected_rec = round(amount * prob, 2)
                rec_action = get_recommended_action(prob, amount, fraud_flag)
                
                # Check policy config for state transitions
                case_status = "FAILED"
                if fraud_flag:
                    case_status = "STOPPED"
                elif rec_action == "MANUAL_REVIEW":
                    case_status = "MANUAL_REVIEW"
                elif prob >= 0.70 and amount <= 40000.0:
                    case_status = "ACTION_PENDING"
                elif rec_action != "STOP":
                    case_status = "RECOVERY_ELIGIBLE"
                else:
                    case_status = "STOPPED"
                
                # Simulating execution results for historical transactions (e.g. 70% of those eligible get executed and some recover)
                # Let's say: if transaction was created more than 3 days ago, and was eligible for recovery, we resolve it.
                recovered_amount = 0.0
                retry_count = 0
                
                is_resolved = (datetime.utcnow() - tx_time).days > 3
                
                if is_resolved and case_status in ["ACTION_PENDING", "RECOVERY_ELIGIBLE", "MANUAL_REVIEW"]:
                    # Simulate outcomes
                    outcome_rand = random.random()
                    if outcome_rand < prob and case_status != "STOPPED":
                        case_status = "RECOVERED"
                        recovered_amount = amount
                        # Update customer history with retry success
                        c_hist[2] += 1
                        retry_count = random.randint(1, 2)
                    else:
                        case_status = "STOPPED"
                        retry_count = 3
                
                case = RecoveryCase(
                    transaction_id=tx_id,
                    status=case_status,
                    recovery_probability=prob,
                    expected_recovery=expected_rec,
                    recommended_action=rec_action,
                    retry_count=retry_count,
                    max_retries=3,
                    created_at=tx_time + timedelta(minutes=2),
                    updated_at=tx_time + timedelta(hours=random.randint(1, 48)) if is_resolved else tx_time + timedelta(minutes=2)
                )
                db.add(case)
                
                # Add historical actions and audit logs for completed recovery cases
                db.flush() # get case.id
                
                # Log audit: Analysis
                audit_analysis = AuditLog(
                    transaction_id=tx_id,
                    recovery_case_id=case.id,
                    timestamp=tx_time + timedelta(minutes=1),
                    actor="SYSTEM",
                    action="RISK_ANALYSIS",
                    previous_state="FAILED",
                    new_state="ANALYZING",
                    reason="Transaction failed. Root-cause classification and risk grading initiated.",
                    metadata_json=f'{{"probability": {prob}, "expected_recovery": {expected_rec}, "recommended_action": "{rec_action}"}}'
                )
                db.add(audit_analysis)
                
                if case_status == "RECOVERED":
                    # Add successful action
                    action = RecoveryAction(
                        recovery_case_id=case.id,
                        action_type=rec_action,
                        status="EXECUTED",
                        details=f"Simulated execution. Recovery successful.",
                        created_at=tx_time + timedelta(minutes=5),
                        updated_at=tx_time + timedelta(minutes=10)
                    )
                    db.add(action)
                    
                    audit_exec = AuditLog(
                        transaction_id=tx_id,
                        recovery_case_id=case.id,
                        timestamp=tx_time + timedelta(minutes=5),
                        actor="POLICY",
                        action="EXECUTE_ACTION",
                        previous_state="ACTION_PENDING",
                        new_state="ACTION_EXECUTED",
                        reason=f"Action {rec_action} approved by policy engine. Executed recovery.",
                        metadata_json='{"gateway_response": "captured"}'
                    )
                    db.add(audit_exec)
                    
                    audit_recovered = AuditLog(
                        transaction_id=tx_id,
                        recovery_case_id=case.id,
                        timestamp=tx_time + timedelta(minutes=10),
                        actor="SYSTEM",
                        action="RECOVERY_SUCCESS",
                        previous_state="ACTION_EXECUTED",
                        new_state="RECOVERED",
                        reason=f"Payment recovered. Captured matching transaction amount of {amount}.",
                        metadata_json=f'{{"recovered_amount": {amount}}}'
                    )
                    db.add(audit_recovered)
                elif case_status == "STOPPED" and retry_count > 0:
                    # Failed action
                    action = RecoveryAction(
                        recovery_case_id=case.id,
                        action_type=rec_action,
                        status="FAILED",
                        details=f"Intervention executed but payment failed again.",
                        created_at=tx_time + timedelta(minutes=5),
                        updated_at=tx_time + timedelta(minutes=10)
                    )
                    db.add(action)
                    
                    audit_exec = AuditLog(
                        transaction_id=tx_id,
                        recovery_case_id=case.id,
                        timestamp=tx_time + timedelta(minutes=5),
                        actor="POLICY",
                        action="EXECUTE_ACTION",
                        previous_state="ACTION_PENDING",
                        new_state="ACTION_EXECUTED",
                        reason=f"Action {rec_action} approved by policy. Initiated.",
                        metadata_json='{}'
                    )
                    db.add(audit_exec)
                    
                    audit_stop = AuditLog(
                        transaction_id=tx_id,
                        recovery_case_id=case.id,
                        timestamp=tx_time + timedelta(minutes=15),
                        actor="POLICY",
                        action="STOP_RECOVERY",
                        previous_state="ACTION_EXECUTED",
                        new_state="STOPPED",
                        reason="Maximum retry limit reached or window expired without successful payment.",
                        metadata_json=f'{{"retries": {retry_count}}}'
                    )
                    db.add(audit_stop)
                elif case_status == "STOPPED" and fraud_flag:
                    # Blocked due to policy
                    audit_stop = AuditLog(
                        transaction_id=tx_id,
                        recovery_case_id=case.id,
                        timestamp=tx_time + timedelta(minutes=2),
                        actor="POLICY",
                        action="BLOCK_ACTION",
                        previous_state="ANALYZING",
                        new_state="STOPPED",
                        reason="Fraud risk flag detected. Policy forbids automated recovery interventions.",
                        metadata_json='{"policy_violation": "FRAUD_SUSPECTED"}'
                    )
                    db.add(audit_stop)
                elif case_status == "MANUAL_REVIEW":
                    # Escalated
                    audit_escalate = AuditLog(
                        transaction_id=tx_id,
                        recovery_case_id=case.id,
                        timestamp=tx_time + timedelta(minutes=3),
                        actor="POLICY",
                        action="ESCALATE_MANUAL",
                        previous_state="ANALYZING",
                        new_state="MANUAL_REVIEW",
                        reason="Transaction amount exceeds automatic threshold or confidence is below min threshold.",
                        metadata_json=f'{{"amount": {amount}, "min_confidence": 0.70}}'
                    )
                    db.add(audit_escalate)

        db.commit()
        print("Successfully generated and saved dataset!")
    except Exception as e:
        db.rollback()
        print(f"Error generating dataset: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    populate_data()
