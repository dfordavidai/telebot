"""Publishing workflow: generate picks, store them, send to Telegram, mark posted."""

import asyncio
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session
from app.core.logger import get_logger
from app.models.match import Prediction
from app.engine.picks import PickGenerator
from app.bot.telegram import format_daily_sheet, send_message
from app.services.roi import ROITracker

logger = get_logger(__name__)

RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5


class Publisher:
    """Coordinate the full daily publish pipeline."""

    @staticmethod
    def generate(db_session: Session) -> List[Prediction]:
        """Generate today's picks (also stores them, per PickGenerator)."""
        return PickGenerator.generate_picks(db_session)

    @staticmethod
    def _serialize(predictions: List[Prediction]) -> List[Dict]:
        return [
            {
                "home": p.match.home,
                "away": p.match.away,
                "pick": p.pick,
                "confidence": p.confidence,
                "category": p.category,
            }
            for p in predictions
        ]

    @staticmethod
    async def send_with_retry(text: str, attempts: int = RETRY_ATTEMPTS) -> bool:
        """Send a Telegram message, retrying on failure."""
        for attempt in range(1, attempts + 1):
            ok = await send_message(text)
            if ok:
                return True
            logger.warning(f"Telegram send attempt {attempt}/{attempts} failed")
            if attempt < attempts:
                await asyncio.sleep(RETRY_DELAY_SECONDS)
        logger.error(f"Telegram send failed after {attempts} attempts")
        return False

    @staticmethod
    def mark_posted(db_session: Session, predictions: List[Prediction]) -> None:
        """Mark predictions as posted with a timestamp."""
        now = datetime.utcnow()
        for p in predictions:
            p.posted = True
            p.posted_at = now
        try:
            db_session.commit()
            logger.info(f"Marked {len(predictions)} predictions as posted")
        except Exception as e:
            logger.error(f"Failed to mark predictions posted: {e}")
            db_session.rollback()

    @classmethod
    async def publish_daily(cls, db_session: Session) -> Dict:
        """
        Full pipeline: generate -> store -> send -> mark_posted.

        Returns a summary dict for logging / API responses.
        """
        predictions = cls.generate(db_session)

        if not predictions:
            logger.info("No predictions generated; sending empty sheet notice")
            await cls.send_with_retry(format_daily_sheet([]))
            return {"picks": 0, "sent": True}

        picks_data = cls._serialize(predictions)
        roi_30d = ROITracker.calculate_roi(db_session, days=30)
        text = format_daily_sheet(picks_data, roi_30d)

        sent = await cls.send_with_retry(text)
        if sent:
            cls.mark_posted(db_session, predictions)
        else:
            logger.error("Picks generated and stored but Telegram send failed")

        return {"picks": len(predictions), "sent": sent}
