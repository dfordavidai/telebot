"""ROI and profit tracking for predictions."""

from datetime import datetime, timedelta
from typing import Dict, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.logger import get_logger
from app.models.match import Prediction

logger = get_logger(__name__)


class ROITracker:
    """Track betting ROI and profit metrics."""
    
    @staticmethod
    def calculate_roi(db_session: Session, days: int = 30) -> Dict[str, float]:
        """
        Calculate ROI metrics over specified period.
        
        Returns: {
            "total_picks": int,
            "wins": int,
            "losses": int,
            "win_rate": float,
            "profit": float,
            "roi_percent": float,
            "avg_confidence": float
        }
        """
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        predictions = db_session.query(Prediction).filter(
            Prediction.posted_at >= cutoff_date,
            Prediction.result.in_(["WON", "LOST"])
        ).all()
        
        if not predictions:
            return {
                "total_picks": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "profit": 0.0,
                "roi_percent": 0.0,
                "avg_confidence": 0.0
            }
        
        wins = [p for p in predictions if p.result == "WON"]
        losses = [p for p in predictions if p.result == "LOST"]
        
        total_profit = sum(p.profit or 0 for p in predictions if p.profit)
        total_stake = len(predictions)  # Assuming 1 unit per pick
        
        win_rate = len(wins) / len(predictions) if predictions else 0.0
        roi_percent = (total_profit / total_stake * 100) if total_stake > 0 else 0.0
        avg_confidence = (
            sum(p.confidence for p in predictions) / len(predictions)
            if predictions else 0.0
        )
        
        return {
            "total_picks": len(predictions),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate * 100, 1),
            "profit": round(total_profit, 2),
            "roi_percent": round(roi_percent, 1),
            "avg_confidence": round(avg_confidence, 1)
        }
    
    @staticmethod
    def get_recent_results(db_session: Session, limit: int = 10) -> List[Dict]:
        """Get recent prediction results for display."""
        
        predictions = db_session.query(Prediction).filter(
            Prediction.result.in_(["WON", "LOST", "VOID"])
        ).order_by(Prediction.posted_at.desc()).limit(limit).all()
        
        results = []
        for p in predictions:
            results.append({
                "match": f"{p.match.home} vs {p.match.away}",
                "pick": p.pick,
                "confidence": p.confidence,
                "result": p.result,
                "profit": p.profit,
                "posted_at": p.posted_at.strftime("%Y-%m-%d %H:%M") if p.posted_at else None
            })
        
        return results
    
    @staticmethod
    def monthly_stats(db_session: Session, year: int, month: int) -> Dict:
        """Get stats for specific month."""
        
        from_date = datetime(year, month, 1)
        if month == 12:
            to_date = datetime(year + 1, 1, 1)
        else:
            to_date = datetime(year, month + 1, 1)
        
        predictions = db_session.query(Prediction).filter(
            Prediction.posted_at >= from_date,
            Prediction.posted_at < to_date,
            Prediction.result.in_(["WON", "LOST"])
        ).all()
        
        if not predictions:
            return {
                "month": f"{year}-{month:02d}",
                "picks": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "profit": 0.0
            }
        
        wins = len([p for p in predictions if p.result == "WON"])
        losses = len([p for p in predictions if p.result == "LOST"])
        profit = sum(p.profit or 0 for p in predictions if p.profit)
        
        return {
            "month": f"{year}-{month:02d}",
            "picks": len(predictions),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / len(predictions) * 100, 1),
            "profit": round(profit, 2)
        }
