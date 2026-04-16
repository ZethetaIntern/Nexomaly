"""Data cleaning and preprocessing pipeline."""
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List, Optional

VALID_CATEGORIES = ["electronics","food","travel","clothing","entertainment",
                    "healthcare","utilities","retail","gambling","crypto","other"]

MERCHANT_RISK_MAP = {
    "casino":0.90,"gambling":0.90,"bet":0.85,"crypto":0.80,"bitcoin":0.80,
    "pawn":0.75,"loan":0.70,"offshore":0.85,"unknown":0.70,"anonymous":0.95,
    "wire":0.65,"transfer":0.55,"amazon":0.05,"walmart":0.05,"target":0.05,
    "starbucks":0.02,"uber":0.03,"netflix":0.02,"apple":0.08,"google":0.05,
}

HIGH_RISK_LOCATIONS = {"offshore","anonymous","unknown location","unverified"}


def get_merchant_risk(merchant: str) -> float:
    m = merchant.lower()
    best = 0.10
    for kw, risk in MERCHANT_RISK_MAP.items():
        if kw in m: best = max(best, risk)
    return best


def clean_transaction(tx: Dict[str, Any]) -> Dict[str, Any]:
    c = tx.copy()
    c["amount"]   = float(max(0.01, min(float(tx.get("amount", 0)), 1_000_000)))
    cat = str(tx.get("category","other")).lower().strip()
    c["category"] = cat if cat in VALID_CATEGORIES else "other"
    c["user_id"]  = str(tx.get("user_id","unknown")).strip()[:64]
    c["location"] = str(tx.get("location","unknown")).strip()[:128]
    c["merchant"] = str(tx.get("merchant","unknown")).strip()[:128]
    return c


def preprocess_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    report: Dict[str, Any] = {"steps": [], "original_shape": list(df.shape)}
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]
    report["steps"].append("normalized_column_names")
    numeric_cols   = df.select_dtypes(include=[np.number]).columns.tolist()
    categoric_cols = df.select_dtypes(include=["object"]).columns.tolist()
    missing = int(df.isnull().sum().sum())
    for col in numeric_cols:   df[col].fillna(df[col].median(), inplace=True)
    for col in categoric_cols: df[col].fillna("unknown", inplace=True)
    report["steps"].append(f"filled_missing ({missing})")
    encoded = {}
    for col in categoric_cols:
        if df[col].nunique() <= 50:
            dummies = pd.get_dummies(df[col], prefix=col, drop_first=False)
            df = pd.concat([df.drop(columns=[col]), dummies], axis=1)
            encoded[col] = list(dummies.columns)
    report["encoded_columns"] = encoded
    report["steps"].append("encoded_categoricals")
    from sklearn.preprocessing import StandardScaler
    scale_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                  if c not in ("is_fraud","label","fraud")]
    if scale_cols:
        df[scale_cols] = StandardScaler().fit_transform(df[scale_cols])
    report["steps"].append(f"scaled {len(scale_cols)} numeric cols")
    report["final_shape"] = list(df.shape)
    return df, report


def _detect_columns(df: pd.DataFrame) -> Dict[str, str]:
    mapping = {}
    for col in df.columns:
        c = col.lower()
        if any(k in c for k in ["amount","value","price","sum"]): mapping["amount"] = col
        elif any(k in c for k in ["user","customer","client","account"]): mapping["user_id"] = col
        elif any(k in c for k in ["fraud","label","target","is_fraud"]): mapping["label"] = col
        elif any(k in c for k in ["merchant","vendor","store"]): mapping["merchant"] = col
    return mapping


def extract_required_features(df: pd.DataFrame, label_col: Optional[str] = None) -> Tuple[pd.DataFrame, "pd.Series"]:
    drop_cols = []
    y = None
    for possible in ["is_fraud","fraud","label","target"]:
        if possible in df.columns:
            y = df[possible].astype(int)
            drop_cols.append(possible)
            break
    if label_col and label_col in df.columns:
        y = df[label_col].astype(int)
        drop_cols.append(label_col)
    X = df.drop(columns=drop_cols, errors="ignore").select_dtypes(include=[np.number])
    if y is None:
        y = pd.Series(np.zeros(len(X), dtype=int))
    return X, y
