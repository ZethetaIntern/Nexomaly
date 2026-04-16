"""
05 – SHAP / Feature Contribution Analysis
Run: python ml_notebooks/05_SHAP_Analysis.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from pipeline.features import extract_features, features_to_vector, FEATURE_NAMES
from pipeline.ingestion import generate_synthetic_dataset
from explainability.shap_explainer import explain, top_reasons

plt.style.use('dark_background')

# Generate a high-risk alert and explain it
tx_fraud = {"user_id":"USR-0001","amount":25000,"merchant":"Casino Royal",
            "category":"gambling","location":"offshore"}
tx_normal = {"user_id":"USR-0001","amount":45,"merchant":"Starbucks",
             "category":"food","location":"New York, US"}

for label, tx in [("FRAUD", tx_fraud), ("NORMAL", tx_normal)]:
    f = extract_features(tx)
    from models.ensemble import compute
    ens,*_ = compute(f)
    contribs = explain(f, ens)
    reason   = top_reasons(f, ens)

    print(f"\n{'='*50}")
    print(f"Transaction: {label} | Score: {ens:.1f}")
    print(f"Reason: {reason}")
    print(f"Top contributions:")
    for k,v in list(contribs.items())[:8]:
        bar = '█' * max(1, int(v/3))
        print(f"  {k:<35} {bar} {v:.2f}")

# Plot top contributions for fraud case
f = extract_features(tx_fraud)
from models.ensemble import compute
ens,*_ = compute(f)
contribs = explain(f, ens)

top_items = list(contribs.items())[:10]
names = [k.replace('_',' ') for k,_ in top_items]
vals  = [v for _,v in top_items]

fig, ax = plt.subplots(figsize=(10,5))
colors = ['#ff3560' if v > 5 else '#ffb020' if v > 2 else '#00e080' for v in vals]
ax.barh(names[::-1], vals[::-1], color=colors[::-1])
ax.set_title(f"Feature Contributions for HIGH-RISK Transaction (Score: {ens:.0f})", color='white')
ax.set_xlabel("Contribution to Risk Score")
plt.tight_layout()
plt.savefig("ml_notebooks/05_shap_analysis.png", dpi=150, facecolor="#07090f")
print("\nSaved: ml_notebooks/05_shap_analysis.png")
