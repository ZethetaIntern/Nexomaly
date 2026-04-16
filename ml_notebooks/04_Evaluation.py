"""
04 – Model Evaluation with full metrics
Run: python ml_notebooks/04_Evaluation.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import (classification_report, roc_auc_score,
                              roc_curve, precision_recall_curve, confusion_matrix)
from pipeline.features import FEATURE_NAMES
from pipeline.ingestion import generate_synthetic_dataset
import models.isolation_forest as if_model
import models.random_forest    as rf_model

plt.style.use('dark_background')

df = generate_synthetic_dataset(5000)
X  = df[FEATURE_NAMES].values; y = df['is_fraud'].values
X_train,X_test,y_train,y_test = train_test_split(X,y,test_size=0.2,random_state=42,stratify=y)

import joblib
from config import settings

# IF evaluation
print("=" * 50)
print("ISOLATION FOREST")
if_m    = joblib.load(os.path.join(settings.ML_MODELS_PATH,"isolation_forest.pkl"))
if_pred = (if_m.predict(X_test)==-1).astype(int)
if_scr  = -if_m.decision_function(X_test)
print(classification_report(y_test, if_pred, target_names=["Normal","Fraud"]))
print(f"AUC-ROC: {roc_auc_score(y_test, if_scr):.4f}")

# RF evaluation
print("=" * 50)
print("RANDOM FOREST")
rf_m   = joblib.load(os.path.join(settings.ML_MODELS_PATH,"random_forest.pkl"))
rf_sc  = joblib.load(os.path.join(settings.ML_MODELS_PATH,"rf_scaler.pkl"))
Xs     = rf_sc.transform(X_test)
rf_pred = rf_m.predict(Xs); rf_prob = rf_m.predict_proba(Xs)[:,1]
print(classification_report(y_test, rf_pred, target_names=["Normal","Fraud"]))
print(f"AUC-ROC: {roc_auc_score(y_test, rf_prob):.4f}")

# ROC curves
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("AnomalyOS – Model Evaluation", color="white")

for ax, name, prob in [(axes[0],"Both Models",None),(axes[1],"PR Curve",None)]:
    pass

ax = axes[0]
for name, prob in [("Isolation Forest",if_scr),("Random Forest",rf_prob)]:
    fpr,tpr,_ = roc_curve(y_test, prob)
    auc = roc_auc_score(y_test, prob)
    ax.plot(fpr, tpr, linewidth=2, label=f"{name} (AUC={auc:.3f})")
ax.plot([0,1],[0,1],'--',color='gray',alpha=0.4)
ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
ax.set_title("ROC Curve"); ax.legend()

ax = axes[1]
for name, prob in [("Isolation Forest",if_scr),("Random Forest",rf_prob)]:
    p,r,_ = precision_recall_curve(y_test, prob)
    ax.plot(r, p, linewidth=2, label=name)
ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
ax.set_title("Precision-Recall Curve"); ax.legend()

plt.tight_layout()
plt.savefig("ml_notebooks/04_evaluation.png", dpi=150, facecolor="#07090f")
print("\nSaved: ml_notebooks/04_evaluation.png")
