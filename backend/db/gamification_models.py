"""Gamification models — XP, achievements, challenges, leaderboard."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import Base


class AnalystProfile(Base):
    __tablename__ = "analyst_profiles"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    analyst_name    = Column(String(128), unique=True, nullable=False)
    display_name    = Column(String(128))
    xp              = Column(Integer, default=0)
    level           = Column(Integer, default=1)
    title           = Column(String(64), default="Rookie Analyst")
    total_detections= Column(Integer, default=0)
    total_fp        = Column(Integer, default=0)
    total_cases     = Column(Integer, default=0)
    fraud_prevented = Column(Float, default=0.0)   # $ amount
    avg_response_sec= Column(Float, default=0.0)
    streak_days     = Column(Integer, default=0)
    last_active     = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    achievements    = relationship("Achievement", back_populates="analyst", cascade="all, delete-orphan")
    xp_log          = relationship("XPEvent",    back_populates="analyst", cascade="all, delete-orphan")


class Achievement(Base):
    __tablename__ = "achievements"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    analyst_name  = Column(String(128), ForeignKey("analyst_profiles.analyst_name"))
    badge_key     = Column(String(64), nullable=False)   # e.g. "first_blood"
    badge_name    = Column(String(128))
    description   = Column(Text)
    icon          = Column(String(8))
    xp_awarded    = Column(Integer, default=0)
    unlocked_at   = Column(DateTime, default=datetime.utcnow)
    analyst       = relationship("AnalystProfile", back_populates="achievements")


class XPEvent(Base):
    __tablename__ = "xp_events"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    analyst_name  = Column(String(128), ForeignKey("analyst_profiles.analyst_name"))
    event_type    = Column(String(64))   # detection, fp_penalty, case_closed, pattern, etc.
    xp_delta      = Column(Integer)      # positive or negative
    description   = Column(String(256))
    metadata_json = Column(JSON)
    created_at    = Column(DateTime, default=datetime.utcnow)
    analyst       = relationship("AnalystProfile", back_populates="xp_log")


class DailyChallenge(Base):
    __tablename__ = "daily_challenges"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    challenge_key = Column(String(64))
    title         = Column(String(128))
    description   = Column(Text)
    icon          = Column(String(8))
    target_value  = Column(Float)
    current_value = Column(Float, default=0.0)
    xp_reward     = Column(Integer)
    completed     = Column(Boolean, default=False)
    expires_at    = Column(DateTime)
    created_at    = Column(DateTime, default=datetime.utcnow)


class LeaderboardEntry(Base):
    __tablename__ = "leaderboard"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    analyst_name    = Column(String(128))
    display_name    = Column(String(128))
    xp              = Column(Integer, default=0)
    level           = Column(Integer, default=1)
    detection_rate  = Column(Float, default=0.0)
    fp_rate         = Column(Float, default=0.0)
    cases_closed    = Column(Integer, default=0)
    fraud_prevented = Column(Float, default=0.0)
    response_time   = Column(Float, default=0.0)
    updated_at      = Column(DateTime, default=datetime.utcnow)
