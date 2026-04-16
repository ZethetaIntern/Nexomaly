"""Full test suite – run with: cd backend && pytest tests/ -v"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest, numpy as np
from datetime import datetime

# ── Pipeline ──────────────────────────────────────────────────────────────────
def test_clean_transaction_clamps():
    from pipeline.cleaner import clean_transaction
    tx = {"user_id":"u1","amount":-99,"merchant":"X","category":"food","location":"NY"}
    assert clean_transaction(tx)["amount"] == 0.01

def test_clean_normalises_bad_category():
    from pipeline.cleaner import clean_transaction
    tx = {"user_id":"u1","amount":100,"merchant":"X","category":"WEIRDCAT","location":"NY"}
    assert clean_transaction(tx)["category"] == "other"

def test_feature_extraction_keys():
    from pipeline.features import extract_features, FEATURE_NAMES
    tx = {"user_id":"u1","amount":500,"merchant":"Amazon","category":"food","location":"NY"}
    f  = extract_features(tx, now=datetime(2024,1,2,14,0))
    for k in FEATURE_NAMES: assert k in f, f"Missing feature: {k}"

def test_feature_vector_length():
    from pipeline.features import extract_features, features_to_vector, FEATURE_NAMES
    tx = {"user_id":"u1","amount":500,"merchant":"Amazon","category":"food","location":"NY"}
    assert len(features_to_vector(extract_features(tx))) == len(FEATURE_NAMES)

def test_merchant_risk_known():
    from pipeline.cleaner import get_merchant_risk
    assert get_merchant_risk("Casino Royal") > 0.5
    assert get_merchant_risk("Amazon") < 0.2

# ── Models ────────────────────────────────────────────────────────────────────
def test_statistical_score_range():
    from models.statistical import score
    f = {"amount_zscore":0.2,"is_night":0,"is_high_risk_location":0,
         "merchant_risk_score":0.1,"is_very_high_amount":0,"velocity_ratio":1}
    s = score(f)
    assert 0 <= s <= 100

def test_statistical_score_anomaly_higher():
    from models.statistical import score
    normal = score({"amount_zscore":0.1,"is_night":0,"is_high_risk_location":0,
                    "merchant_risk_score":0.05,"is_very_high_amount":0,"velocity_ratio":1,"amount_vs_user_std":0})
    fraud  = score({"amount_zscore":5.0,"is_night":1,"is_high_risk_location":1,
                    "merchant_risk_score":0.9,"is_very_high_amount":1,"velocity_ratio":8,"amount_vs_user_std":4})
    assert fraud > normal

def test_ensemble_returns_tuple():
    from pipeline.features import extract_features
    from models.ensemble import compute
    tx = {"user_id":"u1","amount":20000,"merchant":"Casino Royal","category":"gambling","location":"offshore"}
    f  = extract_features(tx)
    result = compute(f)
    assert len(result) == 6
    for v in result: assert 0 <= v <= 100

def test_high_risk_scores_high():
    from pipeline.features import extract_features
    from models.ensemble import compute
    tx = {"user_id":"u1","amount":50000,"merchant":"CryptoBridge","category":"crypto","location":"anonymous"}
    f  = extract_features(tx)
    ens, *_ = compute(f)
    assert ens > 30, "High-risk transaction should score above 30"

# ── Scoring / Explainability ──────────────────────────────────────────────────
def test_score_transaction_keys():
    from pipeline.features import extract_features
    from scoring.risk_scorer import score_transaction
    tx = {"user_id":"u1","amount":500,"merchant":"Amazon","category":"food","location":"NY"}
    f  = extract_features(tx)
    out = score_transaction(f, tx)
    for k in ("risk_score","level","reason","feature_contributions","raw_features"):
        assert k in out

def test_level_thresholds():
    from scoring.risk_scorer import _level
    assert _level(75) == "high"
    assert _level(50) == "medium"
    assert _level(20) == "low"

def test_explainer_contributions():
    from pipeline.features import extract_features
    from explainability.shap_explainer import explain
    tx = {"user_id":"u1","amount":5000,"merchant":"Casino Royal","category":"gambling","location":"offshore"}
    f  = extract_features(tx)
    c  = explain(f, 75.0)
    assert isinstance(c, dict) and len(c) > 0

# ── API ───────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    import main
    return TestClient(main.app)

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_dashboard_stats(client):
    r = client.get("/api/metrics/dashboard")
    assert r.status_code == 200
    d = r.json()
    assert "total_alerts_today" in d and "fp_rate_7d" in d

def test_simulate_alert(client):
    r = client.post("/api/alerts/simulate")
    assert r.status_code == 200

def test_list_alerts(client):
    r = client.get("/api/alerts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_alert_filters(client):
    r = client.get("/api/alerts?level=high&limit=5")
    assert r.status_code == 200

def test_cases_crud(client):
    r = client.post("/api/cases", json={"title":"Test Case","description":"Test","priority":"high"})
    assert r.status_code == 200
    cid = r.json()["id"]

    r = client.get(f"/api/cases/{cid}")
    assert r.status_code == 200

    r = client.put(f"/api/cases/{cid}", json={"status":"investigating"})
    assert r.status_code == 200 and r.json()["status"] == "investigating"

    r = client.delete(f"/api/cases/{cid}")
    assert r.status_code == 200

def test_feedback_flow(client):
    # Get an alert to tag
    alerts = client.get("/api/alerts").json()
    if not alerts:
        client.post("/api/alerts/simulate")
        alerts = client.get("/api/alerts").json()
    assert alerts
    a = alerts[0]
    r = client.post("/api/feedback", json={
        "alert_id": a["id"], "transaction_id": a["transaction_id"] or a["id"],
        "analyst": "Sr. Analyst", "label": "false_positive",
        "reason": "Test feedback", "confidence": 0.9
    })
    assert r.status_code == 200

def test_feedback_stats(client):
    r = client.get("/api/feedback/stats")
    assert r.status_code == 200
    assert "total" in r.json()

def test_performance_metrics(client):
    r = client.get("/api/metrics/performance")
    assert r.status_code == 200

def test_model_metrics(client):
    r = client.get("/api/metrics/models")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
