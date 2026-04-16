from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import Base

class Transaction(Base):
    __tablename__ = "transactions"
    id           = Column(String(32), primary_key=True)
    user_id      = Column(String(64), nullable=False, index=True)
    amount       = Column(Float, nullable=False)
    merchant     = Column(String(128))
    category     = Column(String(64))
    location     = Column(String(128))
    hour         = Column(Integer)
    day_of_week  = Column(Integer)
    is_weekend   = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow, index=True)
    source       = Column(String(32), default="simulator")
    alerts       = relationship("Alert", back_populates="transaction", cascade="all, delete-orphan")

class Alert(Base):
    __tablename__ = "alerts"
    id                    = Column(String(32), primary_key=True)
    transaction_id        = Column(String(32), ForeignKey("transactions.id"), nullable=True)
    user_id               = Column(String(64), nullable=False, index=True)
    amount                = Column(Float, nullable=False)
    risk_score            = Column(Float, nullable=False)
    ml_score              = Column(Float, default=0.0)
    statistical_score     = Column(Float, default=0.0)
    behavioral_score      = Column(Float, default=0.0)
    isolation_score       = Column(Float, default=0.0)
    rf_score              = Column(Float, default=0.0)
    level                 = Column(String(16), nullable=False, index=True)
    status                = Column(String(32), default="new", index=True)
    reason                = Column(Text)
    feature_contributions = Column(JSON)
    raw_features          = Column(JSON)
    true_label            = Column(String(16), nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow, index=True)
    transaction           = relationship("Transaction", back_populates="alerts")
    feedbacks             = relationship("Feedback", back_populates="alert", cascade="all, delete-orphan")
    case_links            = relationship("CaseAlert", back_populates="alert", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_alerts_level_status","level","status"),)

class Case(Base):
    __tablename__ = "cases"
    id           = Column(String(32), primary_key=True)
    title        = Column(String(256), nullable=False)
    description  = Column(Text)
    status       = Column(String(32), default="open", index=True)
    priority     = Column(String(16), default="medium")
    assigned_to  = Column(String(128))
    tags         = Column(JSON, default=list)
    notes        = Column(Text)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at    = Column(DateTime, nullable=True)
    alert_links  = relationship("CaseAlert", back_populates="case", cascade="all, delete-orphan")

class CaseAlert(Base):
    __tablename__ = "case_alerts"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    case_id   = Column(String(32), ForeignKey("cases.id"), nullable=False)
    alert_id  = Column(String(32), ForeignKey("alerts.id"), nullable=False)
    linked_at = Column(DateTime, default=datetime.utcnow)
    case      = relationship("Case",  back_populates="alert_links")
    alert     = relationship("Alert", back_populates="case_links")

class Feedback(Base):
    __tablename__ = "feedback"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    alert_id       = Column(String(32), ForeignKey("alerts.id"), nullable=False)
    transaction_id = Column(String(32))
    analyst        = Column(String(128))
    label          = Column(String(32), nullable=False)
    reason         = Column(Text)
    confidence     = Column(Float, default=1.0)
    retrain_used   = Column(Boolean, default=False)
    created_at     = Column(DateTime, default=datetime.utcnow)
    alert          = relationship("Alert", back_populates="feedbacks")

class ModelMetrics(Base):
    __tablename__ = "model_metrics"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    model_name     = Column(String(64))
    version        = Column(String(32))
    precision      = Column(Float, default=0.0)
    recall         = Column(Float, default=0.0)
    f1_score       = Column(Float, default=0.0)
    fp_rate        = Column(Float, default=0.0)
    detection_rate = Column(Float, default=0.0)
    auc_roc        = Column(Float, default=0.0)
    n_samples      = Column(Integer, default=0)
    trained_on     = Column(String(256))
    created_at     = Column(DateTime, default=datetime.utcnow)

class UploadedDataset(Base):
    __tablename__ = "uploaded_datasets"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    filename      = Column(String(256))
    original_name = Column(String(256))
    rows          = Column(Integer, default=0)
    columns       = Column(JSON)
    is_active     = Column(Boolean, default=False)
    preprocessing = Column(JSON)
    created_at    = Column(DateTime, default=datetime.utcnow)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id       = Column(String(64), primary_key=True)
    tx_count      = Column(Integer, default=0)
    total_amount  = Column(Float, default=0.0)
    avg_amount    = Column(Float, default=0.0)
    std_amount    = Column(Float, default=0.0)
    last_tx_at    = Column(DateTime, nullable=True)
    tx_last_hour  = Column(Integer, default=0)
    tx_last_day   = Column(Integer, default=0)
    merchant_hist = Column(JSON, default=dict)
    hour_hist     = Column(JSON, default=dict)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
