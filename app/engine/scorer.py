"""Scoring engine for match analysis and betting opportunities."""

from typing import Tuple
import math
from app.core.logger import get_logger

logger = get_logger(__name__)

# Scoring weights (must sum to 100)
WEIGHTS = {
    "over25": 0.30,      # 30%
    "btts": 0.25,        # 25%
    "xg_total": 0.20,    # 20%
    "odds": 0.15,        # 15%
    "league": 0.10       # 10%
}

# League reliability multipliers (established leagues more trustworthy)
LEAGUE_SCORES = {
    "PL": 0.95, "EPL": 0.95, "PREMIER_LEAGUE": 0.95,
    "LA_LIGA": 0.90, "LALIGA": 0.90, "LIGA_EA_SPORTS": 0.90,
    "SERIE_A": 0.90, "SERIEA": 0.90,
    "LIGUE_1": 0.85, "LIGUE1": 0.85,
    "BUNDESLIGA": 0.90,
    "EREDIVISIE": 0.80,
    "SUPER_LEAGUE": 0.70, "SUPERLIG": 0.70,
}

# Odds scoring: lower odds = higher confidence
MAX_ODDS = 2.3
MIN_ODDS = 1.1


class Scorer:
    """Calculate betting confidence score for matches."""
    
    @staticmethod
    def score_over25(over25_prob: float) -> float:
        """Score Over 2.5 Goals probability (0-1 input → 0-100 scale)."""
        if over25_prob is None:
            return 0.0
        # Clamp to 0-1 and scale to 0-100
        clamped = max(0.0, min(1.0, over25_prob))
        return clamped * 100
    
    @staticmethod
    def score_btts(btts_prob: float) -> float:
        """Score BTTS probability (0-1 input → 0-100 scale)."""
        if btts_prob is None:
            return 0.0
        clamped = max(0.0, min(1.0, btts_prob))
        return clamped * 100
    
    @staticmethod
    def score_xg(xg_home: float, xg_away: float) -> float:
        """Score total Expected Goals (higher total = more goals likely)."""
        if xg_home is None or xg_away is None:
            return 0.0
        
        total_xg = xg_home + xg_away
        # xG 0-5 maps to score 0-100
        # 3.5+ xG is good for Over 2.5
        normalized = min(total_xg / 5.0, 1.0) * 100
        return normalized
    
    @staticmethod
    def score_odds(odds: float) -> float:
        """Score betting odds (lower odds = higher confidence)."""
        if odds is None or odds < MIN_ODDS or odds > MAX_ODDS:
            return 0.0
        
        # Invert: lower odds = higher score
        # MIN_ODDS (1.1) → 100, MAX_ODDS (2.3) → 0
        normalized = ((MAX_ODDS - odds) / (MAX_ODDS - MIN_ODDS)) * 100
        return max(0.0, min(100.0, normalized))
    
    @staticmethod
    def score_league(league: str) -> float:
        """Score league reliability factor."""
        score = LEAGUE_SCORES.get(league, 0.6)  # Default 0.6 for unknown
        return score * 100
    
    @staticmethod
    def calculate_composite(
        over25: float,
        btts: float,
        xg_home: float,
        xg_away: float,
        odds: float,
        league: str
    ) -> int:
        """
        Calculate weighted composite betting score.
        
        Returns: 0-100 normalized score
        """
        
        # Get individual component scores
        over25_score = Scorer.score_over25(over25)
        btts_score = Scorer.score_btts(btts)
        xg_score = Scorer.score_xg(xg_home, xg_away)
        odds_score = Scorer.score_odds(odds)
        league_score = Scorer.score_league(league)
        
        # Apply weights
        weighted = (
            (over25_score * WEIGHTS["over25"]) +
            (btts_score * WEIGHTS["btts"]) +
            (xg_score * WEIGHTS["xg_total"]) +
            (odds_score * WEIGHTS["odds"]) +
            (league_score * WEIGHTS["league"])
        )
        
        # Normalize to 0-100
        final_score = min(100, max(0, weighted))
        
        logger.debug(
            f"Score breakdown: Over25={over25_score:.0f}, "
            f"BTTS={btts_score:.0f}, xG={xg_score:.0f}, "
            f"Odds={odds_score:.0f}, League={league_score:.0f} → "
            f"Final={final_score:.0f}"
        )
        
        return int(round(final_score))
    
    @staticmethod
    def categorize_pick(score: int) -> str:
        """Categorize pick by confidence level."""
        if score >= 80:
            return "SAFE"
        elif score >= 75:
            return "VALUE"
        else:
            return "HIGH_RISK"
