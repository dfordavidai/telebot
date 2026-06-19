"""Generate and select betting picks from scored matches."""

from typing import List, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.logger import get_logger
from app.core.config import get_settings
from app.models.match import Match, Prediction
from app.engine.scorer import Scorer

logger = get_logger(__name__)


class PickGenerator:
    """Generate and select best betting picks."""
    
    @staticmethod
    def generate_picks(db_session: Session, for_date: datetime = None) -> List[Prediction]:
        """
        Generate picks for specified date (default: today).
        
        Process:
        1. Query matches for date with score >= MIN_SCORE
        2. Determine best market (Over2.5 or BTTS)
        3. Create Prediction records
        4. Limit to MAX_DAILY_PICKS
        """
        
        settings = get_settings()
        if for_date is None:
            for_date = datetime.utcnow().date()
        
        # Get matches for date without existing picks
        matches = db_session.query(Match).filter(
            Match.date >= datetime.combine(for_date, datetime.min.time()),
            Match.date < datetime.combine(for_date, datetime.max.time()),
            Match.status == "pending",
            ~Match.predictions.any()  # Not already scored
        ).all()
        
        logger.info(f"Found {len(matches)} unscored matches for {for_date}")
        
        picks = []
        for match in matches:
            # Calculate composite score
            score = Scorer.calculate_composite(
                over25=match.over25,
                btts=match.btts,
                xg_home=match.xg_home,
                xg_away=match.xg_away,
                odds=match.odds,
                league=match.league
            )
            
            # Only create pick if meets minimum threshold
            if score < settings.MIN_SCORE:
                logger.debug(
                    f"{match.home} vs {match.away}: score {score} < {settings.MIN_SCORE}"
                )
                continue
            
            # Store score on match
            match.score = score
            
            # Determine best pick (market)
            best_pick, pick_confidence = PickGenerator._select_market(
                match.over25,
                match.btts,
                score
            )
            
            # Categorize pick
            category = Scorer.categorize_pick(score)
            
            # Create Prediction record
            prediction = Prediction(
                match_id=match.id,
                pick=best_pick,
                confidence=pick_confidence,
                category=category,
                result="PENDING",
                posted=False
            )
            picks.append(prediction)
        
        logger.info(f"Generated {len(picks)} picks from {len(matches)} matches")
        
        # Sort by confidence descending and limit
        picks_sorted = sorted(picks, key=lambda p: p.confidence, reverse=True)
        picks_limited = picks_sorted[:settings.MAX_DAILY_PICKS]
        
        # Save to database
        for pick in picks_limited:
            db_session.add(pick)
        
        try:
            db_session.commit()
            logger.info(f"Saved {len(picks_limited)} picks to database")
        except Exception as e:
            logger.error(f"Failed to save picks: {e}")
            db_session.rollback()
            return []
        
        return picks_limited
    
    @staticmethod
    def _select_market(over25_prob: float, btts_prob: float, composite_score: int) -> tuple:
        """
        Select best market (Over2.5 or BTTS) based on probabilities.
        
        Returns: (market_name, confidence_score)
        """
        
        if over25_prob is None and btts_prob is None:
            return ("Over2.5", composite_score)
        
        # If only one available, pick it
        if over25_prob is None:
            return ("BTTS", min(100, int(btts_prob * 100)))
        if btts_prob is None:
            return ("Over2.5", min(100, int(over25_prob * 100)))
        
        # Both available: pick the one with higher probability
        over25_score = int(over25_prob * 100)
        btts_score = int(btts_prob * 100)
        
        if over25_score >= btts_score:
            return ("Over2.5", over25_score)
        else:
            return ("BTTS", btts_score)
