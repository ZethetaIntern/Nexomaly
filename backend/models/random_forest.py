"""Random Forest – supervised fraud classifier."""
import os, sys
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.features import features_to_vector, FEATURE_NAMES
from config import settings

MODEL_PATH  = os.path.join(settings.ML_MODELS_PATH, "random_forest.pkl")
SCALER_PATH = os.path.join(settings.ML_MODELS_PATH, "rf_scaler.pkl")
_model = _scaler = None


def _get_model():
    global _model, _scaler
    if _model is None:
        if os.path.exists(MODEL_PATH):
            _model  = joblib.load(MODEL_PATH)
            _scaler = joblib.load(SCALER_PATH) if os.path.exists(SCALER_PATH) else None
        else:
            _model, _scaler = _train_default()
    return _model, _scaler


def _train_default():
    from pipeline.ingestion import generate_synthetic_dataset
    from sklearn.model_selection import train_test_split
    import numpy as np
    df = generate_synthetic_dataset(5000)
    X  = df[FEATURE_NAMES].values + np.random.normal(0, 0.05, (len(df), len(FEATURE_NAMES)))
    y  = df["is_fraud"].values
    return train(X, y)


def train(X: np.ndarray, y: np.ndarray):
    global _model, _scaler
    sc = StandardScaler()
    Xs = sc.fit_transform(X)
    m  = RandomForestClassifier(n_estimators=200, max_depth=12,
                                 min_samples_leaf=5, class_weight="balanced",
                                 random_state=42, n_jobs=-1)
    m.fit(Xs, y)
    os.makedirs(settings.ML_MODELS_PATH, exist_ok=True)
    joblib.dump(m,  MODEL_PATH)
    joblib.dump(sc, SCALER_PATH)
    _model  = m
    _scaler = sc
    print(f"[RF] Saved → {MODEL_PATH}")
    return m, sc


def score(features: dict) -> float:
    """Fraud probability 0–100."""
    m, sc = _get_model()
    vec   = np.array(features_to_vector(features)).reshape(1, -1)
    if sc: vec = sc.transform(vec)
    return float(m.predict_proba(vec)[0][1] * 100)


def get_feature_importances() -> dict:
    m, _ = _get_model()
    return dict(zip(FEATURE_NAMES, m.feature_importances_.tolist()))


def reload():
    global _model, _scaler; _model = _scaler = None
    return _get_model()
