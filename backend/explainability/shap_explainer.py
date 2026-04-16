"""SHAP-style feature contribution explainer."""
import numpy as np
from typing import Dict, List
from pipeline.features import FEATURE_NAMES, features_to_vector

_IMPORTANCES = {
    "amount_zscore":0.18,"amount_vs_user_std":0.14,"merchant_risk_score":0.13,
    "is_high_risk_location":0.10,"velocity_ratio":0.09,"is_new_merchant":0.08,
    "is_very_high_amount":0.07,"is_night":0.06,"log_amount":0.05,
    "is_high_risk_category":0.04,"is_weekend":0.03,"amount_x_merchant_risk":0.03,
    "amount_x_night":0.02,"user_tx_last_hour":0.02,"amount_vs_user_avg":0.02,
    "is_high_amount":0.02,"amount":0.01,"hour":0.01,"day_of_week":0.005,
    "is_business_hours":0.005,"user_tx_count":0.005,"user_tx_last_day":0.005,
}


def explain(features: Dict[str, float], risk_score: float) -> Dict[str, float]:
    contribs: Dict[str, float] = {}
    for name in FEATURE_NAMES:
        val = features.get(name, 0.0)
        imp = _IMPORTANCES.get(name, 0.01)
        if name in ("amount","log_amount"):
            norm = min(abs(val)/20000, 1.0)
        elif name in ("amount_zscore","amount_vs_user_std","amount_vs_user_avg"):
            norm = min(abs(val)/5.0, 1.0)
        elif name == "velocity_ratio":
            norm = min(abs(val)/10.0, 1.0)
        else:
            norm = float(np.clip(abs(val), 0, 1))
        contribs[name] = round(imp * norm * 100, 3)
    total = sum(contribs.values())
    if total > 0:
        factor = risk_score / total
        contribs = {k: round(v * factor, 2) for k, v in contribs.items()}
    return dict(sorted(contribs.items(), key=lambda x: -x[1]))


def top_reasons(features: Dict[str, float], risk_score: float, n: int = 3) -> str:
    reasons = []
    if abs(features.get("amount_vs_user_std",0)) > 2.5:
        reasons.append("Amount far above user average")
    elif abs(features.get("amount_zscore",0)) > 2.5:
        reasons.append("Statistical amount outlier")
    elif features.get("is_very_high_amount"):
        reasons.append("Very high transaction amount")
    elif features.get("is_high_amount"):
        reasons.append("High transaction amount")
    if features.get("merchant_risk_score",0) > 0.6: reasons.append("High-risk merchant")
    if features.get("is_high_risk_location"):        reasons.append("Suspicious location")
    if features.get("is_night"):                     reasons.append("Unusual time (night)")
    if features.get("velocity_ratio",1) > 4:         reasons.append("Elevated transaction velocity")
    if features.get("is_new_merchant"):              reasons.append("New/unseen merchant")
    if features.get("is_high_risk_category"):        reasons.append("High-risk category")
    if not reasons: reasons.append("ML ensemble anomaly pattern")
    return "; ".join(reasons[:n])


def update_importances_from_model(importances: Dict[str, float]):
    global _IMPORTANCES
    _IMPORTANCES.update(importances)
