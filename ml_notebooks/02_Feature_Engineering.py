"""
02 – Feature Engineering Analysis
Run: python ml_notebooks/02_Feature_Engineering.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pipeline.features import extract_features, FEATURE_NAMES, features_to_vector
from pipeline.ingestion import generate_synthetic_dataset

plt.style.use('dark_background')

print("Building feature matrix...")
df = generate_synthetic_dataset(2000)
feature_rows = []
for _, row in df.iterrows():
    tx = row.to_dict()
    f  = extract_features(tx)
    feature_rows.append(features_to_vector(f))

X = pd.DataFrame(feature_rows, columns=FEATURE_NAMES)
y = df['is_fraud'].values

print(f"Feature matrix: {X.shape}")
print(f"\nFeature stats (fraud vs normal):")
for col in FEATURE_NAMES[:10]:
    fraud_mean  = X[y==1][col].mean()
    normal_mean = X[y==0][col].mean()
    print(f"  {col:<30} fraud={fraud_mean:.3f}  normal={normal_mean:.3f}")

# Correlation with label
corr_with_fraud = X.corrwith(pd.Series(y)).abs().sort_values(ascending=False)
print(f"\nTop correlated features:\n{corr_with_fraud.head(10)}")

fig, ax = plt.subplots(figsize=(10, 6))
corr_with_fraud.head(12).plot(kind='barh', ax=ax, color='#00e5cf')
ax.set_title('Feature Correlation with Fraud Label', color='white')
ax.invert_yaxis()
plt.tight_layout()
plt.savefig('ml_notebooks/02_feature_importance.png', dpi=150, facecolor='#07090f')
print("\nSaved: ml_notebooks/02_feature_importance.png")
