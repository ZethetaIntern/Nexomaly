"""Alert engine: transaction → clean → features → score → persist."""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from pipeline.cleaner import clean_transaction
from pipeline.features import extract_features, update_user_profile
from scoring.risk_scorer import score_transaction
import sys,os; sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models import Alert, Transaction, UserProfile

ALERT_THRESHOLD = 20.0


def process(tx_data: Dict[str, Any], db: Session, save: bool=True,
            now: Optional[datetime]=None) -> Optional[Dict[str, Any]]:
    if now is None: now = datetime.utcnow()
    tx_data  = clean_transaction(tx_data)
    user_id  = tx_data["user_id"]
    profile  = None

    if save:
        up = db.query(UserProfile).filter(UserProfile.user_id==user_id).first()
        if up:
            profile = {"tx_count":up.tx_count,"avg_amount":up.avg_amount,"std_amount":up.std_amount,
                       "total_amount":up.total_amount,"tx_last_hour":up.tx_last_hour,
                       "tx_last_day":up.tx_last_day,"merchant_hist":up.merchant_hist or {},
                       "hour_hist":up.hour_hist or {},
                       "last_tx_at":up.last_tx_at.isoformat() if up.last_tx_at else None}

    features = extract_features(tx_data, user_profile=profile, now=now)
    scored   = score_transaction(features, tx_data)

    if save: _update_profile(user_id, tx_data, now, db)

    if scored["risk_score"] < ALERT_THRESHOLD:
        if save: _save_tx(tx_data, None, now, db)
        return None

    tx_id    = "TX-"  + uuid.uuid4().hex[:8].upper()
    alert_id = "ALT-" + uuid.uuid4().hex[:6].upper()
    alert_data = {"id":alert_id,"transaction_id":tx_id,"user_id":user_id,
                  "amount":tx_data["amount"],**scored,"status":"new","created_at":now}

    if save:
        _save_tx(tx_data, tx_id, now, db)
        _save_alert(alert_data, db)

    return {k:(v.isoformat() if isinstance(v,datetime) else v) for k,v in alert_data.items()}


def _save_tx(tx_data, tx_id, now, db):
    if tx_id is None: tx_id = "TX-"+uuid.uuid4().hex[:8].upper()
    t = Transaction(id=tx_id,user_id=tx_data["user_id"],amount=tx_data["amount"],
                    merchant=tx_data.get("merchant"),category=tx_data.get("category"),
                    location=tx_data.get("location"),hour=now.hour,day_of_week=now.weekday(),
                    is_weekend=(now.weekday()>=5),created_at=now)
    db.add(t); db.flush()


def _save_alert(data, db):
    db.add(Alert(
        id=data["id"],transaction_id=data.get("transaction_id"),user_id=data["user_id"],
        amount=data["amount"],risk_score=data["risk_score"],ml_score=data["ml_score"],
        statistical_score=data["statistical_score"],behavioral_score=data["behavioral_score"],
        isolation_score=data["isolation_score"],rf_score=data["rf_score"],
        level=data["level"],status=data["status"],reason=data["reason"],
        feature_contributions=data.get("feature_contributions"),
        raw_features=data.get("raw_features"),created_at=data["created_at"]))
    db.commit()


def _update_profile(user_id, tx_data, now, db):
    up = db.query(UserProfile).filter(UserProfile.user_id==user_id).first()
    if not up:
        up = UserProfile(user_id=user_id,tx_count=0,total_amount=0.0,avg_amount=0.0,
                          std_amount=0.0,tx_last_hour=0,tx_last_day=0,merchant_hist={},hour_hist={})
        db.add(up); db.flush()
    pdict = {"tx_count":up.tx_count,"avg_amount":up.avg_amount,"std_amount":up.std_amount,
             "total_amount":up.total_amount,"tx_last_hour":up.tx_last_hour,
             "tx_last_day":up.tx_last_day,"merchant_hist":up.merchant_hist or {},
             "hour_hist":up.hour_hist or {},
             "last_tx_at":up.last_tx_at.isoformat() if up.last_tx_at else None}
    upd = update_user_profile(pdict, tx_data, now)
    up.tx_count=upd["tx_count"]; up.avg_amount=upd["avg_amount"]; up.std_amount=upd["std_amount"]
    up.total_amount=upd["total_amount"]; up.tx_last_hour=upd.get("tx_last_hour",0)
    up.tx_last_day=upd.get("tx_last_day",0); up.merchant_hist=upd.get("merchant_hist",{})
    up.hour_hist=upd.get("hour_hist",{}); up.last_tx_at=now
    db.flush()
