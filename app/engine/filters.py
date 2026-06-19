"""Pre-scoring filters to reject low-quality or invalid matches."""

from typing import Optional
from app.core.logger import get_logger
from app.core.config import get_settings
from app.engine.scorer import LEAGUE_SCORES

logger = get_logger(__name__)

MAX_ODDS = 2.3
KNOWN_LEAGUES = set(LEAGUE_SCORES.keys())


class MatchFilter:
    """Reject matches that don't meet minimum quality criteria."""

    @staticmethod
    def has_required_xg(xg_home: Optional[float], xg_away: Optional[float]) -> bool:
        """Reject matches missing xG data."""
        return xg_home is not None and xg_away is not None

    @staticmethod
    def odds_in_range(odds: Optional[float]) -> bool:
        """Reject matches with odds above the configured ceiling."""
        if odds is None:
            return False
        return odds <= MAX_ODDS

    @staticmethod
    def is_known_league(league: Optional[str]) -> bool:
        """Reject matches from unrecognized leagues."""
        if not league:
            return False
        return league.upper() in KNOWN_LEAGUES

    @staticmethod
    def passes_score_threshold(score: int) -> bool:
        """Reject matches scoring below the configured minimum."""
        settings = get_settings()
        return score >= settings.MIN_SCORE

    @classmethod
    def is_eligible(
        cls,
        xg_home: Optional[float],
        xg_away: Optional[float],
        odds: Optional[float],
        league: Optional[str],
    ) -> bool:
        """
        Run all pre-scoring eligibility checks.

        Duplicate detection is handled separately at the import layer
        (see CSVImporter.import_matches), since it requires a DB session.
        """
        checks = [
            cls.has_required_xg(xg_home, xg_away),
            cls.odds_in_range(odds),
            cls.is_known_league(league),
        ]

        if not all(checks):
            logger.debug(
                f"Match filtered out: league={league}, odds={odds}, "
                f"xg_home={xg_home}, xg_away={xg_away}"
            )
            return False

        return True
