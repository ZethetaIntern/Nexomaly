"""Model training orchestrator with full metrics and feedback loop."""
import os, sys
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sklearn.metrics import (precision_score, recall_score, f1_score,
                              roc_auc_score, confusion_matrix)
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.features import FEATURE_NAMES
from pipeline.ingestion import generate_synthetic_dataset, get_active_dataset
import models.isolation_forest as if_model
import models.random_forest    as rf_model
from models.ensemble import reload_all
from explainability.shap_explainer import update_importances_from_model
from db.models import Feedback, Alert, ModelMetrics
from config import settings


def train_all(db: Session, model_types: List[str] = None,
              use_feedback: bool = True, dataset_id: Optional[int] = None) -> Dict[str, Any]:
    if model_types is None:
        model_types = ["isolation_forest", "random_forest"]
    print("[Trainer] Loading training data...")
    X, y, source = _load_data(db, use_feedback, dataset_id)
    print(f"[Trainer] {len(X)} samples | {int(y.sum())} fraud | src: {source}")
    metrics, trained = {}, []
    if "isolation_forest" in model_types:
        cont = float(np.clip(y.mean(), 0.05, 0.4)) if y.mean() > 0.01 else 0.12
        if_model.train(X, contamination=cont)
        m = _eval_if(X, y); metrics["isolation_forest"] = m
        _save_metrics(db, "isolation_forest", m, source, len(X))
        trained.append("isolation_forest")
    if "random_forest" in model_types:
        model, scaler = rf_model.train(X, y)
        m = _eval_rf(model, scaler, X, y); metrics["random_forest"] = m
        _save_metrics(db, "random_forest", m, source, len(X))
        update_importances_from_model(rf_model.get_feature_importances())
        trained.append("random_forest")
    reload_all()
    return {"trained": trained, "metrics": metrics, "samples": int(len(X)),
            "source": source, "timestamp": datetime.utcnow().isoformat()}


def _load_data(db, use_feedback, dataset_id):
    if dataset_id:
        from db.models import UploadedDataset
        ds = db.query(UploadedDataset).filter(UploadedDataset.id == dataset_id).first()
        if ds:
            path = os.path.join(settings.DATA_PATH, "processed", ds.filename)
            if os.path.exists(path):
                df = pd.read_csv(path)
                X, y = _extract_Xy(df)
                if use_feedback: X, y, src = _augment(db, X, y, ds.original_name); return X, y, src
                return X, y, ds.original_name
    active = get_active_dataset(db)
    if active:
        df, meta = active; X, y = _extract_Xy(df); source = meta.get("original_name","active_upload")
    else:
        df = generate_synthetic_dataset(5000); X = df[FEATURE_NAMES].values; y = df["is_fraud"].values; source = "synthetic"
    if use_feedback: X, y, source = _augment(db, X, y, source)
    return X, y, source


def _extract_Xy(df):
    feats = [f for f in FEATURE_NAMES if f in df.columns]
    if not feats:
        feats = [c for c in df.select_dtypes(include=[np.number]).columns if c not in ("is_fraud","fraud","label","target")]
    lc = next((c for c in ("is_fraud","fraud","label","target") if c in df.columns), None)
    X  = df[feats].fillna(0).values
    y  = df[lc].astype(int).values if lc else np.zeros(len(X), dtype=int)
    return X, y


def _augment(db, X, y, source):
    fbs = db.query(Feedback).filter(Feedback.retrain_used == False).all()
    if not fbs: return X, y, source
    eX, ey = [], []
    for fb in fbs:
        alert = db.query(Alert).filter(Alert.id == fb.alert_id).first()
        if alert and alert.raw_features:
            from pipeline.features import features_to_vector
            vec = features_to_vector(alert.raw_features)
            lbl = 1 if fb.label == "true_positive" else 0
            reps = max(1, int(fb.confidence * 5))
            eX.extend([vec]*reps); ey.extend([lbl]*reps)
    if eX:
        X = np.vstack([X, np.array(eX)]); y = np.concatenate([y, np.array(ey)])
        for fb in fbs: fb.retrain_used = True
        db.commit(); source += f"+{len(eX)}fb"
    return X, y, source


def _eval_if(X, y):
    import joblib
    from sklearn.model_selection import train_test_split
    # Split BEFORE evaluating — never test on training data
    _, X_te, _, y_te = train_test_split(
        X, y, test_size=0.25, random_state=42,
        stratify=y if y.sum() > 5 else None
    )
    m = joblib.load(os.path.join(settings.ML_MODELS_PATH, "isolation_forest.pkl"))
    preds  = (m.predict(X_te) == -1).astype(int)
    scores = -m.decision_function(X_te)
    return _metrics(y_te, preds, scores)


def _eval_rf(model, scaler, X, y):
    from sklearn.model_selection import train_test_split
    # Split BEFORE evaluating
    _, X_te, _, y_te = train_test_split(
        X, y, test_size=0.25, random_state=42,
        stratify=y if y.sum() > 5 else None
    )
    Xs = scaler.transform(X_te) if scaler else X_te
    return _metrics(y_te, model.predict(Xs), model.predict_proba(Xs)[:, 1])


def _metrics(y, preds, proba):
    if len(np.unique(y)) < 2:
        return dict(precision=0,recall=0,f1_score=0,fp_rate=0,detection_rate=0,auc_roc=0,tp=0,fp=0,tn=0,fn=0)
    try: auc = float(roc_auc_score(y, proba))
    except: auc = 0.0
    try: tn,fp,fn,tp = confusion_matrix(y, preds, labels=[0,1]).ravel()
    except: tn=fp=fn=tp=0
    return dict(
        precision=round(float(precision_score(y,preds,zero_division=0)),4),
        recall=round(float(recall_score(y,preds,zero_division=0)),4),
        f1_score=round(float(f1_score(y,preds,zero_division=0)),4),
        fp_rate=round(fp/(fp+tn) if (fp+tn)>0 else 0.0,4),
        detection_rate=round(tp/(tp+fn) if (tp+fn)>0 else 0.0,4),
        auc_roc=round(auc,4), tp=int(tp),fp=int(fp),tn=int(tn),fn=int(fn))


def _save_metrics(db, name, m, source, n):
    db.add(ModelMetrics(
        model_name=name, version=f"v{datetime.utcnow().strftime('%Y%m%d%H%M')}",
        precision=m.get("precision",0), recall=m.get("recall",0), f1_score=m.get("f1_score",0),
        fp_rate=m.get("fp_rate",0), detection_rate=m.get("detection_rate",0),
        auc_roc=m.get("auc_roc",0), n_samples=n, trained_on=source))
    db.commit()
