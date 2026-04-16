"""
03 – Model Training
Run: python ml_notebooks/03_Model_Training.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

import numpy as np
from sklearn.model_selection import train_test_split
from pipeline.features import FEATURE_NAMES
from pipeline.ingestion import generate_synthetic_dataset
import models.isolation_forest as if_model
import models.random_forest    as rf_model

print("Generating training data...")
df = generate_synthetic_dataset(5000)
X  = df[FEATURE_NAMES].values
y  = df['is_fraud'].values
X_train,X_test,y_train,y_test = train_test_split(X,y,test_size=0.2,random_state=42,stratify=y)

print(f"Train: {len(X_train)} | Test: {len(X_test)}")
print(f"Fraud rate: {y_train.mean()*100:.1f}% train | {y_test.mean()*100:.1f}% test")

print("\nTraining Isolation Forest...")
if_model.train(X_train, contamination=float(y_train.mean()))

print("Training Random Forest...")
rf_model.train(X_train, y_train)

print("\nModels saved to backend/models/saved/")
print("Run 04_Evaluation.py to see metrics.")
