"""Custom dataset ingestion pipeline."""
import os, uuid
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings
from pipeline.cleaner import preprocess_dataframe, _detect_columns


def generate_synthetic_dataset(n: int = 5000) -> pd.DataFrame:
    np.random.seed(42)
    M_N = ["Amazon","Walmart","Target","Best Buy","Apple Store","Shell Gas",
           "Starbucks","Delta Airlines","Uber","Netflix","McDonald's","Costco"]
    M_R = ["Casino Royal","CryptoBridge","PawnShop Plus","LoanShark Finance",
           "Unknown Vendor","Wire Transfer Co","OffshoreBank"]
    C_N = ["food","clothing","utilities","retail","healthcare"]
    C_R = ["gambling","crypto","travel","electronics"]
    L_N = ["New York, US","San Francisco, US","Chicago, US","London, UK",
           "Tokyo, JP","Austin, US","Seattle, US","Miami, US"]
    L_R = ["offshore","anonymous","Unknown Location"]
    rows = []
    for _ in range(n):
        fraud = np.random.random() < 0.12
        if fraud:
            amount   = float(np.random.lognormal(7, 1.8))   # was 8,1.5 — more overlap
            hour     = int(np.random.choice([0,1,2,3,4,5,22,23,14,15]))  # some daytime fraud
            merchant = np.random.choice(M_R + M_N[:4])       # sometimes normal merchants
            category = np.random.choice(C_R + C_N[:2])       # sometimes normal categories
            location = np.random.choice(L_R + L_N[:3])       # sometimes normal locations
        else:
            amount=float(np.random.lognormal(5.0,0.7)); hour=int(np.random.randint(8,20))
            merchant=np.random.choice(M_N); category=np.random.choice(C_N); location=np.random.choice(L_N)
        dow=int(np.random.randint(0,7))
        rows.append({
            "user_id": f"USR-{str(int(np.random.randint(1,201))).zfill(4)}",
            "amount": round(amount,2), "merchant": merchant, "category": category,
            "location": location, "hour": hour, "day_of_week": dow,
            "is_weekend": int(dow>=5), "is_night": int(hour<6 or hour>22),
            "log_amount": round(np.log1p(amount),4),
            "amount_zscore": round((amount-250)/400,4),
            "is_high_amount": int(amount>1000), "is_very_high_amount": int(amount>5000),
            "is_high_risk_merchant": int(merchant in M_R),
            "is_high_risk_category": int(category in C_R),
            "is_high_risk_location": int(location in L_R),
            "merchant_risk_score": np.random.uniform(0.6,0.95) if fraud else np.random.uniform(0.01,0.2),
            "velocity_ratio": np.random.uniform(3,10) if fraud else np.random.uniform(0.5,2),
            "amount_vs_user_avg": np.random.uniform(2,8) if fraud else np.random.uniform(-1,1),
            "amount_vs_user_std": np.random.uniform(2,6) if fraud else np.random.uniform(-1,1),
            "is_new_merchant": int(fraud and np.random.random()<0.7),
            "user_tx_count": int(np.random.randint(1,500)),
            "user_tx_last_hour": int(np.random.randint(3,15) if fraud else np.random.randint(0,3)),
            "user_tx_last_day": int(np.random.randint(10,50) if fraud else np.random.randint(1,10)),
            "is_business_hours": int(9<=hour<=17 and dow<5),
            "amount_x_merchant_risk": 0, "amount_x_night": 0,
            "is_fraud": int(fraud),
        })
    df = pd.DataFrame(rows)
    os.makedirs(os.path.join(settings.DATA_PATH,"raw"), exist_ok=True)
    df.to_csv(os.path.join(settings.DATA_PATH,"raw","synthetic_transactions.csv"), index=False)
    return df


def ingest_csv(file_path: str, original_name: str, db: Session) -> Tuple[bool, Dict[str, Any]]:
    try: df = pd.read_csv(file_path)
    except Exception as e: return False, {"error": f"Could not read CSV: {e}"}
    if len(df) < 10: return False, {"error": "Dataset too small (min 10 rows)"}
    if len(df.columns) < 2: return False, {"error": "Need at least 2 columns"}
    col_map = _detect_columns(df)
    columns_list = list(df.columns)
    try: processed_df, report = preprocess_dataframe(df)
    except Exception as e: return False, {"error": f"Preprocessing failed: {e}"}
    proc_fn = f"dataset_{uuid.uuid4().hex[:8]}.csv"
    proc_path = os.path.join(settings.DATA_PATH, "processed", proc_fn)
    os.makedirs(os.path.dirname(proc_path), exist_ok=True)
    processed_df.to_csv(proc_path, index=False)
    from db.models import UploadedDataset
    ds = UploadedDataset(filename=proc_fn, original_name=original_name,
                          rows=len(df), columns=columns_list, is_active=False, preprocessing=report)
    db.add(ds); db.commit(); db.refresh(ds)
    return True, {"dataset_id": ds.id, "rows": len(df), "columns": columns_list,
                  "col_mapping": col_map, "preprocessing": report, "processed_path": proc_path}


def activate_dataset(dataset_id: int, db: Session) -> bool:
    from db.models import UploadedDataset
    db.query(UploadedDataset).update({"is_active": False})
    ds = db.query(UploadedDataset).filter(UploadedDataset.id == dataset_id).first()
    if not ds: return False
    ds.is_active = True; db.commit(); return True


def get_active_dataset(db: Session):
    from db.models import UploadedDataset
    ds = db.query(UploadedDataset).filter(UploadedDataset.is_active == True).first()
    if not ds: return None
    path = os.path.join(settings.DATA_PATH, "processed", ds.filename)
    if not os.path.exists(path): return None
    df = pd.read_csv(path)
    return df, {"dataset_id": ds.id, "rows": ds.rows, "original_name": ds.original_name}
