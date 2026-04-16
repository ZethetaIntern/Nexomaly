"""
01 – Exploratory Data Analysis
Run: python ml_notebooks/01_EDA.py
(Or open as Jupyter notebook by renaming to .ipynb)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pipeline.ingestion import generate_synthetic_dataset

plt.style.use('dark_background')
sns.set_palette("husl")

print("Generating synthetic dataset...")
df = generate_synthetic_dataset(5000)
print(f"Shape: {df.shape}")
print(f"\nClass balance:\n{df['is_fraud'].value_counts()}")
print(f"\nFraud rate: {df['is_fraud'].mean()*100:.1f}%")
print(f"\nAmount stats:\n{df['amount'].describe()}")
print(f"\nFraud amount mean: ${df[df.is_fraud==1]['amount'].mean():,.2f}")
print(f"Normal amount mean: ${df[df.is_fraud==0]['amount'].mean():,.2f}")

fig, axes = plt.subplots(2, 3, figsize=(15, 8))
fig.suptitle('AnomalyOS — EDA', fontsize=14, color='white')

# Amount distribution
ax = axes[0,0]
ax.hist(np.log1p(df[df.is_fraud==0]['amount']), bins=40, alpha=0.6, label='Normal', color='#00e5cf')
ax.hist(np.log1p(df[df.is_fraud==1]['amount']), bins=40, alpha=0.6, label='Fraud',  color='#ff3560')
ax.set_title('Log Amount Distribution'); ax.legend()

# Hour distribution
ax = axes[0,1]
df[df.is_fraud==0].groupby('hour').size().plot(ax=ax, color='#00e5cf', label='Normal', linewidth=2)
df[df.is_fraud==1].groupby('hour').size().plot(ax=ax, color='#ff3560', label='Fraud',  linewidth=2)
ax.set_title('Transactions by Hour'); ax.legend()

# Merchant risk
ax = axes[0,2]
means = df.groupby('is_fraud')['merchant_risk_score'].mean()
ax.bar(['Normal','Fraud'], means.values, color=['#00e5cf','#ff3560'])
ax.set_title('Mean Merchant Risk Score')

# Category
ax = axes[1,0]
fraud_cat = df[df.is_fraud==1]['category'].value_counts().head(6)
ax.barh(fraud_cat.index, fraud_cat.values, color='#ff3560')
ax.set_title('Top Fraud Categories')

# Correlation heatmap
ax = axes[1,1]
num_cols = ['amount','is_night','merchant_risk_score','velocity_ratio','is_high_risk_location','is_fraud']
corr = df[num_cols].corr()
sns.heatmap(corr, ax=ax, cmap='RdYlGn', center=0, annot=True, fmt='.2f', cbar=False)
ax.set_title('Feature Correlation')

# Fraud by location
ax = axes[1,2]
loc_fraud = df.groupby('is_high_risk_location')['is_fraud'].mean()
ax.bar(['Normal Location','High Risk Location'], loc_fraud.values, color=['#00e080','#ff3560'])
ax.set_title('Fraud Rate by Location Risk')

plt.tight_layout()
plt.savefig('ml_notebooks/01_eda_plots.png', dpi=150, bbox_inches='tight', facecolor='#07090f')
print("\nSaved: ml_notebooks/01_eda_plots.png")
plt.show()
