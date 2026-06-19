"""Database models for matches and predictions."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.storage.database import Base


class Match(Base):
    """Match details with statistics."""
    
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    league = Column(String, nullable=False, index=True)
    home = Column(String, nullable=False)
    away = Column(String, nullable=False)
    xg_home = Column(Float, nullable=True)
    xg_away = Column(Float, nullable=True)
    btts = Column(Float, nullable=True)  # Probability 0-1
    over25 = Column(Float, nullable=True)  # Probability 0-1
    odds = Column(Float, nullable=True)
    score = Column(Integer, nullable=True)  # Our betting score 0-100
    status = Column(String, default="pending")  # pending, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    predictions = relationship("Prediction", back_populates="match")
    
    def __repr__(self) -> str:
        return f"<Match {self.home} vs {self.away} ({self.date.date()})>"


class Prediction(Base):
    """Prediction/pick details with result tracking."""
    
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    pick = Column(String, nullable=False)  # Over2.5, BTTS
    confidence = Column(Integer, nullable=False)  # 0-100
    category = Column(String, nullable=False)  # SAFE, VALUE, HIGH_RISK
    result = Column(String, nullable=True)  # WON, LOST, VOID, PENDING
    profit = Column(Float, nullable=True)  # Stake units won/lost
    posted = Column(Boolean, default=False, index=True)
    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    match = relationship("Match", back_populates="predictions")
    
    def __repr__(self) -> str:
        return f"<Prediction {self.pick} (confidence={self.confidence})>"
