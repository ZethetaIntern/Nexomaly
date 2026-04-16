"""Feature engineering – 22 features per transaction."""
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional

FEATURE_NAMES = [
    "amount","log_amount","amount_zscore","amount_vs_user_avg","amount_vs_user_std",
    "is_high_amount","is_very_high_amount","user_tx_count","user_tx_last_hour",
    "user_tx_last_day","velocity_ratio","hour","day_of_week","is_weekend","is_night",
    "is_business_hours","merchant_risk_score","is_high_risk_location","is_high_risk_category",
    "is_new_merchant","amount_x_merchant_risk","amount_x_night",
]

HIGH_RISK_CATEGORIES = {"gambling","crypto","travel","electronics"}
HIGH_RISK_LOCATIONS  = {"offshore","anonymous","unknown location","unverified"}
GLOBAL_AMT_MEAN, GLOBAL_AMT_STD = 250.0, 400.0


def extract_features(tx: Dict[str, Any], user_profile: Optional[Dict]=None,
                     now: Optional[datetime]=None) -> Dict[str, float]:
    if now is None: now = datetime.utcnow()
    amount   = float(tx.get("amount",0))
    merchant = str(tx.get("merchant","")).lower()
    category = str(tx.get("category","")).lower()
    location = str(tx.get("location","")).lower()
    hour, dow = now.hour, now.weekday()

    log_amount    = float(np.log1p(amount))
    amount_zscore = (amount - GLOBAL_AMT_MEAN) / max(GLOBAL_AMT_STD, 1.0)

    if user_profile and user_profile.get("tx_count",0)>0:
        u_avg  = float(user_profile.get("avg_amount", GLOBAL_AMT_MEAN))
        u_std  = max(float(user_profile.get("std_amount", GLOBAL_AMT_STD)), 1.0)
        a_avg  = float(np.clip((amount-u_avg)/u_avg if u_avg>0 else 0, -10,10))
        a_std  = float(np.clip((amount-u_avg)/u_std, -10,10))
        tx_cnt = int(user_profile.get("tx_count",0))
        tx_hr  = int(user_profile.get("tx_last_hour",0))
        tx_day = int(user_profile.get("tx_last_day",0))
        vel    = float(np.clip(tx_hr/max(tx_day/24.0,0.1), 0, 50))
        mh     = user_profile.get("merchant_hist",{})
        new_m  = int(merchant not in mh)
    else:
        a_avg=amount_zscore; a_std=amount_zscore; tx_cnt=0; tx_hr=0; tx_day=0; vel=1.0; new_m=1

    from pipeline.cleaner import get_merchant_risk, HIGH_RISK_LOCATIONS as HRL
    m_risk = get_merchant_risk(merchant)

    return {
        "amount":               amount,
        "log_amount":           log_amount,
        "amount_zscore":        float(amount_zscore),
        "amount_vs_user_avg":   a_avg,
        "amount_vs_user_std":   a_std,
        "is_high_amount":       float(amount>1000),
        "is_very_high_amount":  float(amount>5000),
        "user_tx_count":        float(min(tx_cnt,10000)),
        "user_tx_last_hour":    float(tx_hr),
        "user_tx_last_day":     float(tx_day),
        "velocity_ratio":       vel,
        "hour":                 float(hour),
        "day_of_week":          float(dow),
        "is_weekend":           float(dow>=5),
        "is_night":             float(hour<6 or hour>22),
        "is_business_hours":    float(9<=hour<=17 and dow<5),
        "merchant_risk_score":  m_risk,
        "is_high_risk_location":float(any(h in location for h in HRL)),
        "is_high_risk_category":float(category in HIGH_RISK_CATEGORIES),
        "is_new_merchant":      float(new_m),
        "amount_x_merchant_risk": float(amount_zscore * m_risk),
        "amount_x_night":       float(amount_zscore * int(hour<6 or hour>22)),
    }


def features_to_vector(features: Dict[str, float]) -> list:
    return [features.get(k, 0.0) for k in FEATURE_NAMES]


def update_user_profile(profile: Dict[str, Any], tx: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    p = profile.copy()
    amount   = float(tx.get("amount",0))
    merchant = str(tx.get("merchant","")).lower()
    n        = p.get("tx_count",0)+1
    old_mean = p.get("avg_amount",amount)
    delta    = amount - old_mean
    new_mean = old_mean + delta/n
    old_m2   = (p.get("std_amount",0.0)**2)*max(n-1,1)
    new_m2   = old_m2 + delta*(amount-new_mean)
    p.update({"tx_count":n,"total_amount":p.get("total_amount",0.0)+amount,
              "avg_amount":new_mean,"std_amount":float(np.sqrt(new_m2/n)) if n>1 else 0.0,
              "last_tx_at":now.isoformat()})
    mh = p.get("merchant_hist",{}); mh[merchant]=mh.get(merchant,0)+1; p["merchant_hist"]=mh
    hh = p.get("hour_hist",{});     hr=str(now.hour); hh[hr]=hh.get(hr,0)+1; p["hour_hist"]=hh
    last = p.get("last_tx_at")
    if last:
        try:
            diff = (now - datetime.fromisoformat(last)).total_seconds()/3600
            if diff<1:  p["tx_last_hour"]=p.get("tx_last_hour",0)+1
            if diff<24: p["tx_last_day"]=p.get("tx_last_day",0)+1
            else:       p["tx_last_hour"]=0; p["tx_last_day"]=1
        except: pass
    p["updated_at"]=now.isoformat()
    return p
