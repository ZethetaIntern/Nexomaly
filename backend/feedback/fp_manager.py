"""Feedback collection and FP rate tracking."""
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models import Feedback, Alert


def submit(db, alert_id, transaction_id, analyst, label, reason, confidence=1.0) -> Feedback:
    fb = Feedback(alert_id=alert_id, transaction_id=transaction_id,
                  analyst=analyst, label=label, reason=reason,
                  confidence=confidence, retrain_used=False, created_at=datetime.utcnow())
    db.add(fb)
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.status      = "false_positive" if label == "false_positive" else "resolved"
        alert.true_label  = "normal" if label == "false_positive" else "fraud"
    db.commit(); db.refresh(fb)
    return fb

def list_all(db, limit=200) -> List[Feedback]:
    return db.query(Feedback).order_by(Feedback.created_at.desc()).limit(limit).all()

def stats(db) -> Dict:
    total = db.query(Feedback).count()
    fp    = db.query(Feedback).filter(Feedback.label=="false_positive").count()
    since = datetime.utcnow() - timedelta(days=7)
    t7    = db.query(Feedback).filter(Feedback.created_at>=since).count()
    fp7   = db.query(Feedback).filter(Feedback.created_at>=since,
                                      Feedback.label=="false_positive").count()
    pending = db.query(Feedback).filter(Feedback.retrain_used==False).count()
    return {"total": total, "false_positives": fp,
            "fp_rate": round(fp7/t7*100,1) if t7>0 else 0.0,
            "pending_retrain": pending}
