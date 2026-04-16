"""Ensemble scorer – combines all models."""
import os, sys, json
from typing import Dict, Tuple, Any
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import models.isolation_forest as _if
import models.random_forest    as _rf
import models.statistical      as _stat
from config import settings

WEIGHTS_PATH = os.path.join(settings.ML_MODELS_PATH, "ensemble_weights.json")
DEFAULT_W = {"isolation_forest": 0.35, "random_forest": 0.40,
             "statistical": 0.15, "behavioral": 0.10}


def _behavioral(f: dict) -> float:
    s  = f.get("is_night", 0) * 20
    s += f.get("is_new_merchant", 0) * 15
    s += f.get("is_high_risk_location", 0) * 20
    s += f.get("merchant_risk_score", 0) * 25
    s += min(f.get("velocity_ratio", 1) * 2, 20)
    if f.get("is_weekend") and f.get("is_very_high_amount"): s += 10
    return min(float(s), 100.0)


def load_weights() -> Dict[str, float]:
    try:
        if os.path.exists(WEIGHTS_PATH):
            return json.load(open(WEIGHTS_PATH))
    except Exception:
        pass
    return DEFAULT_W.copy()


def compute(features: Dict[str, Any]) -> Tuple[float, float, float, float, float, float]:
    """Returns (ensemble, if_score, rf_score, stat_score, behav_score, ml_score)."""
    w   = load_weights()
    ifs = _if.score(features)
    rfs = _rf.score(features)
    sts = _stat.score(features)
    bhs = _behavioral(features)
    wif = w.get("isolation_forest", 0.35)
    wrf = w.get("random_forest",    0.40)
    mls = (ifs * wif + rfs * wrf) / max(wif + wrf, 1e-9)
    ens = wif*ifs + wrf*rfs + w.get("statistical",0.15)*sts + w.get("behavioral",0.10)*bhs
    return (round(float(ens),2), round(ifs,2), round(rfs,2),
            round(sts,2), round(bhs,2), round(float(mls),2))


def reload_all():
    _if.reload(); _rf.reload()
