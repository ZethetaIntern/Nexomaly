"""Isolation Forest – unsupervised anomaly detection."""
import os, sys
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest as _IF
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.features import features_to_vector, FEATURE_NAMES
from config import settings

MODEL_PATH = os.path.join(settings.ML_MODELS_PATH, "isolation_forest.pkl")
_model = None


def _get_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            _model = joblib.load(MODEL_PATH)
        else:
            _model = _train_default()
    return _model


def _train_default():
    from pipeline.ingestion import generate_synthetic_dataset
    df = generate_synthetic_dataset(5000)
    X  = df[FEATURE_NAMES].values
    # Add noise so model doesn't overfit
    import numpy as np
    X = X + np.random.normal(0, 0.1, X.shape)
    return train(X, contamination=0.12)

def train(X: np.ndarray, contamination: float = 0.12):
    global _model
    m = _IF(n_estimators=200, contamination=contamination,
            max_samples="auto", random_state=42, n_jobs=-1)
    m.fit(X)
    os.makedirs(settings.ML_MODELS_PATH, exist_ok=True)
    joblib.dump(m, MODEL_PATH)
    _model = m
    print(f"[IF] Saved → {MODEL_PATH}")
    return m


def score(features: dict) -> float:
    """Anomaly score 0–100. Higher = more anomalous."""
    m   = _get_model()
    vec = np.array(features_to_vector(features)).reshape(1, -1)
    raw = m.decision_function(vec)[0]          # negative → anomalous
    return float(np.clip((1 - (raw + 0.5)) * 100, 0, 100))


def reload():
    global _model; _model = None
    return _get_model()
