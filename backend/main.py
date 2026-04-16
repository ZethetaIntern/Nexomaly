import asyncio, sys, os
from datetime import datetime, timedelta
from typing import List
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from db.database import engine, Base, SessionLocal
from db.models import (Transaction, Alert, Case, CaseAlert, Feedback,
                       ModelMetrics, UploadedDataset, UserProfile)
from db.gamification_models import (AnalystProfile, Achievement,
                                     XPEvent, DailyChallenge, LeaderboardEntry)

# ── Create all tables ──────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── Pre-warm ML models ─────────────────────────────────────────────────────────
print("[Startup] Warming ML models …")
from models.isolation_forest import _get_model as _warm_if
from models.random_forest    import _get_model as _warm_rf
_warm_if(); _warm_rf()
print("[Startup] Models ready ✓")

# ── Seed demo data ─────────────────────────────────────────────────────────────
def _seed_demo_data():
    import random
    db = SessionLocal()
    try:
        if db.query(Case).count() > 0:
            # Still seed gamification if missing
            from gamification.engine import seed_demo_gamification
            seed_demo_gamification(db)
            return

        now = datetime.utcnow()

        # Sample Cases
        cases = [
            Case(id="CASE-DEMO01", title="Offshore Wire Transfer Cluster",
                 description="Multiple high-value transactions routed through offshore accounts detected over a 48h window. Users USR-0042 and USR-0078 flagged by the ensemble model.",
                 status="investigating", priority="high", assigned_to="Sr. Analyst",
                 tags=["offshore","wire-transfer","cluster"],
                 notes="INVESTIGATION LOG\n\n[Day 1] Initial Review:\nReviewed flagged transactions for USR-0042 and USR-0078. Both accounts show wire transfers to the same offshore routing number within 48 hours.\n\n[Day 1] Actions Taken:\n- Submitted True Positive feedback on both alerts\n- Escalated to compliance team\n- Temporary hold placed on both accounts",
                 created_at=now-timedelta(hours=6), updated_at=now-timedelta(hours=2)),
            Case(id="CASE-DEMO02", title="Casino Merchant Spike — USR-0015",
                 description="USR-0015 made 7 transactions to Casino Royal within 2 hours totalling $34,200. Velocity anomaly triggered RF model at 91% fraud probability.",
                 status="open", priority="high", assigned_to="Sr. Analyst",
                 tags=["gambling","velocity","high-amount"],
                 notes=None,
                 created_at=now-timedelta(hours=14), updated_at=now-timedelta(hours=14)),
            Case(id="CASE-DEMO03", title="Crypto Exchange — Coordinated Accounts",
                 description="Three accounts (USR-0101, USR-0134, USR-0189) all transacted to CryptoBridge within the same 15-minute window from different locations.",
                 status="open", priority="medium", assigned_to="Sr. Analyst",
                 tags=["crypto","coordinated","multi-account"],
                 notes=None,
                 created_at=now-timedelta(hours=26), updated_at=now-timedelta(hours=26)),
            Case(id="CASE-DEMO04", title="False Positive Review — Low-risk Travel",
                 description="Flight bookings for USR-0055 triggered travel category alerts. Confirmed legitimate — user on business trip.",
                 status="resolved", priority="low", assigned_to="Sr. Analyst",
                 tags=["false-positive","travel","resolved"],
                 notes="Confirmed legitimate with user. Added to whitelist.",
                 created_at=now-timedelta(days=2), updated_at=now-timedelta(hours=18),
                 closed_at=now-timedelta(hours=18)),
            Case(id="CASE-DEMO05", title="PawnShop Transaction — Unusual Hours",
                 description="USR-0033 made $8,500 transaction to PawnShop Plus at 2:47 AM on a Sunday.",
                 status="investigating", priority="medium", assigned_to="Sr. Analyst",
                 tags=["pawnshop","night","weekend"],
                 notes="Called customer — voicemail. Sent email verification request.",
                 created_at=now-timedelta(hours=9), updated_at=now-timedelta(hours=3)),
        ]
        for c in cases:
            db.add(c)
        db.flush()

        # Demo alerts + feedback (no fake 100% model metrics)
        demo_txs = [
            ("USR-0055",  320.0,  "Delta Airlines",   "low",    "false_positive",
             "Confirmed legitimate — customer verified business trip"),
            ("USR-0021",  150.0,  "Amazon",           "low",    "false_positive",
             "Regular purchase pattern, no anomaly detected"),
            ("USR-0042", 18500.0, "Casino Royal",     "high",   "true_positive",
             "Confirmed fraud — customer reported unauthorized charge"),
            ("USR-0078",  9200.0, "Wire Transfer Co", "high",   "true_positive",
             "Wire to unknown offshore account — customer confirmed fraud"),
            ("USR-0015",  4400.0, "CryptoBridge",     "high",   "true_positive",
             "Multiple crypto transactions — account compromised"),
            ("USR-0033",  8500.0, "PawnShop Plus",    "high",   "true_positive",
             "Night transaction, high-risk merchant — confirmed fraud"),
            ("USR-0099",   75.0,  "Starbucks",        "low",    "false_positive",
             "Normal daily purchase, model over-triggered"),
        ]

        for i, (uid, amt, merchant, level, label, reason) in enumerate(demo_txs):
            tx_id  = f"TX-SEED{str(i).zfill(4)}"
            alt_id = f"ALT-SEED{str(i).zfill(2)}"
            days_ago = random.randint(1, 5)
            score = 85.0 if label == "true_positive" else 35.0

            tx = Transaction(id=tx_id, user_id=uid, amount=amt, merchant=merchant,
                             category="other", location="New York, US",
                             hour=14, day_of_week=1, is_weekend=False,
                             created_at=now-timedelta(days=days_ago))
            db.add(tx); db.flush()

            alert = Alert(id=alt_id, transaction_id=tx_id, user_id=uid, amount=amt,
                          risk_score=score, ml_score=score-5, statistical_score=score-10,
                          behavioral_score=score-8, isolation_score=score-3, rf_score=score-2,
                          level=level,
                          status="false_positive" if label=="false_positive" else "resolved",
                          reason=f"Demo: {reason[:60]}",
                          true_label="normal" if label=="false_positive" else "fraud",
                          created_at=now-timedelta(days=days_ago))
            db.add(alert); db.flush()

            fb = Feedback(alert_id=alt_id, transaction_id=tx_id, analyst="Sr. Analyst",
                          label=label, reason=reason, confidence=0.95,
                          retrain_used=True,
                          created_at=now-timedelta(days=days_ago))
            db.add(fb)

        # Seed gamification
        from gamification.engine import seed_demo_gamification
        seed_demo_gamification(db)

        db.commit()
        print("[Seed] Demo data inserted ✓ (5 cases, 7 feedback)")
    except Exception as e:
        db.rollback()
        print(f"[Seed] Error: {e}")
    finally:
        db.close()

_seed_demo_data()

# ── WebSocket manager ──────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self): self.active: List[WebSocket] = []
    async def connect(self, ws):
        await ws.accept(); self.active.append(ws)
    def disconnect(self, ws):
        if ws in self.active: self.active.remove(ws)
    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:    await ws.send_json(data)
            except: dead.append(ws)
        for ws in dead: self.disconnect(ws)

manager = ConnectionManager()

# ── Background simulator ───────────────────────────────────────────────────────
async def _simulation_loop():
    await asyncio.sleep(5)
    from streaming.simulator import generate_transaction
    from alerts.alert_engine  import process
    while True:
        if settings.SIMULATION_ENABLED:
            try:
                db    = SessionLocal()
                tx    = generate_transaction()
                alert = process(tx, db, save=True)
                if alert:
                    await manager.broadcast({"type":"alert","data":alert})
                db.close()
            except Exception as e:
                print(f"[Sim] Error: {e}")
        await asyncio.sleep(settings.SIMULATION_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_simulation_loop())
    yield

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="AnomalyOS API", version=settings.VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ── Routers ────────────────────────────────────────────────────────────────────
from routers.alerts       import router as r_alerts
from routers.cases        import router as r_cases
from routers.feedback     import router as r_feedback
from routers.metrics      import router as r_metrics
from routers.data         import router as r_data
from routers.gamification import router as r_gamification

app.include_router(r_alerts)
app.include_router(r_cases)
app.include_router(r_feedback)
app.include_router(r_metrics)
app.include_router(r_data)
app.include_router(r_gamification)

# ── WebSocket ──────────────────────────────────────────────────────────────────
@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(25)
            try: await websocket.send_json({"type":"ping","ts":datetime.utcnow().isoformat()})
            except: break
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status":"ok","app":settings.APP_NAME,"version":settings.VERSION,
            "time":datetime.utcnow().isoformat()}

# ── Serve frontend ─────────────────────────────────────────────────────────────
FRONTEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND):
    app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
    @app.get("/")
    def root(): return FileResponse(os.path.join(FRONTEND,"index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)
