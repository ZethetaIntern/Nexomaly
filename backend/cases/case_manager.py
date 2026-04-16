"""Case management CRUD."""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models import Case, CaseAlert, Alert


def create(db, title, description="", priority="medium",
           assigned_to="Sr. Analyst", tags=None, alert_ids=None) -> Case:
    c = Case(id="CASE-"+uuid.uuid4().hex[:6].upper(), title=title,
             description=description, priority=priority, assigned_to=assigned_to,
             tags=tags or [], created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db.add(c); db.flush()
    for aid in (alert_ids or []):
        db.add(CaseAlert(case_id=c.id, alert_id=aid))
    db.commit(); db.refresh(c)
    return c

def list_all(db) -> List[Case]:
    return db.query(Case).order_by(Case.created_at.desc()).all()

def get(db, case_id) -> Optional[Case]:
    return db.query(Case).filter(Case.id == case_id).first()

def update(db, case_id, **kwargs) -> Optional[Case]:
    c = get(db, case_id)
    if not c: return None
    for k, v in kwargs.items():
        if v is not None and hasattr(c, k): setattr(c, k, v)
    c.updated_at = datetime.utcnow()
    if kwargs.get("status") in ("resolved","closed"):
        c.closed_at = datetime.utcnow()
    db.commit(); db.refresh(c)
    return c

def delete(db, case_id) -> bool:
    c = get(db, case_id)
    if not c: return False
    db.delete(c); db.commit(); return True

def link_alert(db, case_id, alert_id) -> bool:
    exists = db.query(CaseAlert).filter(
        CaseAlert.case_id==case_id, CaseAlert.alert_id==alert_id).first()
    if exists: return False
    db.add(CaseAlert(case_id=case_id, alert_id=alert_id))
    db.commit(); return True

def get_alert_count(db, case_id) -> int:
    return db.query(CaseAlert).filter(CaseAlert.case_id==case_id).count()
