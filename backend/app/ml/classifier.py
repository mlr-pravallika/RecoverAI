import os
import joblib
import pandas as pd
from sqlalchemy.orm import Session
from backend.app.models import models

# Load model pipeline
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")
model_pipeline = None

try:
    if os.path.exists(MODEL_PATH):
        model_pipeline = joblib.load(MODEL_PATH)
        print("ML Model loaded successfully in classifier module.")
except Exception as e:
    print(f"Error loading ML model: {e}")

def get_customer_payment_history(db: Session, customer_id: str, before_timestamp=None):
    # Query transactions for customer
    query = db.query(models.Transaction)
    if before_timestamp:
        query = query.filter(models.Transaction.created_at < before_timestamp)
    
    txs = query.filter(models.Transaction.customer_id == customer_id).all()
    success_count = sum(1 for t in txs if t.status == 'captured')
    failure_count = sum(1 for t in txs if t.status == 'failed')
    
    return success_count, failure_count

def predict_recovery_probability(
    db: Session,
    amount: float,
    payment_method: str,
    failure_code: str,
    customer_id: str,
    before_timestamp=None
) -> float:
    # 1. Check if fraud
    if failure_code == "BAD_REQUEST_PAYMENT_RISK_THRESHOLD_EXCEEDED":
        return 0.0
        
    # Get history
    prev_success_count, prev_failure_count = get_customer_payment_history(db, customer_id, before_timestamp)
    
    # 2. Try to run ML model
    if model_pipeline is not None:
        try:
            # Create a DataFrame for prediction matching training feature columns
            df_input = pd.DataFrame([{
                "amount": amount,
                "payment_method": payment_method or "unknown",
                "failure_code": failure_code or "unknown",
                "prev_success_count": prev_success_count,
                "prev_failure_count": prev_failure_count
            }])
            
            # Predict probability of class 1 (recovered)
            probs = model_pipeline.predict_proba(df_input)[0]
            # class 1 probability is index 1
            prob = float(probs[1])
            return round(prob, 2)
        except Exception as e:
            print(f"Prediction failed, falling back to heuristic: {e}")
            
    # Heuristics fallback
    if failure_code == "GATEWAY_ERROR":
        return 0.90
    elif failure_code == "BAD_REQUEST_PAYMENT_CARD_EXPIRED":
        return 0.05
    else:
        total = prev_success_count + prev_failure_count
        if total > 0:
            return round((prev_success_count + 1) / (total + 2), 2)
        return 0.50
