import sys
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.core.database import SessionLocal
from backend.app.models.models import Transaction, RecoveryCase, Customer

def train_model():
    print("Loading data from database...")
    db = SessionLocal()
    try:
        # Load all failed transactions that have a recovery case (which contains the outcome)
        query = db.query(
            Transaction.id,
            Transaction.customer_id,
            Transaction.amount,
            Transaction.payment_method,
            Transaction.failure_code,
            Transaction.created_at,
            RecoveryCase.status.label("recovery_status")
        ).join(
            RecoveryCase, Transaction.id == RecoveryCase.transaction_id
        )
        
        df = pd.read_sql(query.statement, db.bind)
        print(f"Loaded {len(df)} failed transactions with recovery outcomes.")
        
        if len(df) < 50:
            print("Not enough data to train. Exiting.")
            return
            
        # Calculate historical features for each transaction
        # To avoid data leakage, we compute history using only events before the transaction's created_at
        all_tx = pd.read_sql(db.query(
            Transaction.id, Transaction.customer_id, Transaction.status, Transaction.created_at
        ).statement, db.bind)
        all_tx['created_at'] = pd.to_datetime(all_tx['created_at'])
        df['created_at'] = pd.to_datetime(df['created_at'])
        
        # Sort transactions by time to optimize or do it iteratively
        all_tx = all_tx.sort_values('created_at')
        
        prev_successes = []
        prev_failures = []
        
        for idx, row in df.iterrows():
            cust_id = row['customer_id']
            tx_time = row['created_at']
            
            # Filter history
            cust_history = all_tx[(all_tx['customer_id'] == cust_id) & (all_tx['created_at'] < tx_time)]
            
            success_count = sum(cust_history['status'] == 'captured')
            failure_count = sum(cust_history['status'] == 'failed')
            
            prev_successes.append(success_count)
            prev_failures.append(failure_count)
            
        df['prev_success_count'] = prev_successes
        df['prev_failure_count'] = prev_failures
        
        # Target variable: Was the case recovered?
        # status RECOVERED = 1, otherwise (STOPPED, MANUAL_REVIEW, etc.) = 0
        df['target'] = (df['recovery_status'] == 'RECOVERED').astype(int)
        
        # Features and target split
        feature_cols = [
            'amount', 'payment_method', 'failure_code', 
            'prev_success_count', 'prev_failure_count'
        ]
        
        X = df[feature_cols].copy()
        y = df['target'].values
        
        # Fill missing values if any
        X['payment_method'] = X['payment_method'].fillna('unknown')
        X['failure_code'] = X['failure_code'].fillna('unknown')
        
        # Define preprocessing pipeline
        categorical_features = ['payment_method', 'failure_code']
        numeric_features = ['amount', 'prev_success_count', 'prev_failure_count']
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', 'passthrough', numeric_features),
                ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
            ]
        )
        
        # Pipeline with preprocessor and RandomForest classifier
        model_pipeline = Pipeline(
            steps=[
                ('preprocessor', preprocessor),
                ('classifier', RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42))
            ]
        )
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        print("Training model...")
        model_pipeline.fit(X_train, y_train)
        
        # Evaluation
        y_pred = model_pipeline.predict(X_test)
        report = classification_report(y_test, y_pred)
        cm = confusion_matrix(y_test, y_pred)
        
        print("\nEvaluation Report:")
        print(report)
        print("Confusion Matrix:")
        print(cm)
        
        # Save evaluation report to text file
        os.makedirs(os.path.dirname(__file__), exist_ok=True)
        eval_path = os.path.join(os.path.dirname(__file__), "evaluation.txt")
        with open(eval_path, "w") as f:
            f.write("ML Recovery Probability Model Evaluation\n")
            f.write("=========================================\n\n")
            f.write(report)
            f.write("\nConfusion Matrix:\n")
            f.write(str(cm))
        print(f"Saved evaluation report to {eval_path}")
        
        # Save the model
        model_path = os.path.join(os.path.dirname(__file__), "model.joblib")
        joblib.dump(model_pipeline, model_path)
        print(f"Saved trained model to {model_path}")
        
    finally:
        db.close()

if __name__ == "__main__":
    train_model()
