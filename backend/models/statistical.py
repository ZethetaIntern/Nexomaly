"""Statistical baseline scorer."""

def score(features: dict) -> float:
    s  = min(abs(features.get("amount_zscore", 0)) * 18, 50)
    s += abs(features.get("amount_vs_user_std", 0)) * 5
    s += features.get("is_night", 0) * 12
    s += features.get("is_high_risk_location", 0) * 18
    s += features.get("merchant_risk_score", 0) * 20
    s += features.get("is_very_high_amount", 0) * 8
    s += min(features.get("velocity_ratio", 1) * 3, 15)
    return min(float(s), 100.0)
