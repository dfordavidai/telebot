"""Daily scheduler: import -> score -> publish at POST_HOUR (TIMEZONE)."""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import get_settings
from app.core.logger import get_logger
from app.storage.database import db
from app.data.importer import CSVImporter
from app.services.publisher import Publisher

logger = get_logger(__name__)

JOB_RETRY_ATTEMPTS = 3
JOB_RETRY_DELAY_SECONDS = 30


async def run_daily_job() -> None:
    """
    Full daily pipeline: import CSV -> score & generate picks -> publish to Telegram.

    Retries the whole pipeline up to JOB_RETRY_ATTEMPTS times on unexpected
    failure (network blips, transient DB issues, etc).
    """
    for attempt in range(1, JOB_RETRY_ATTEMPTS + 1):
        session = db.get_session()
        try:
            logger.info(f"Daily job starting (attempt {attempt}/{JOB_RETRY_ATTEMPTS})")

            importer = CSVImporter()
            imported = importer.import_matches(session)
            logger.info(f"Imported {imported} new matches")

            result = await Publisher.publish_daily(session)
            logger.info(f"Daily job complete: {result}")
            return
        except Exception as e:
            logger.error(f"Daily job failed on attempt {attempt}: {e}")
            if attempt < JOB_RETRY_ATTEMPTS:
                await asyncio.sleep(JOB_RETRY_DELAY_SECONDS)
            else:
                logger.error("Daily job failed after all retry attempts")
        finally:
            session.close()


def build_scheduler() -> AsyncIOScheduler:
    """Build and configure the AsyncIO scheduler with the daily cron job."""
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)

    scheduler.add_job(
        run_daily_job,
        trigger=CronTrigger(hour=settings.POST_HOUR, minute=0),
        id="daily_footy_pipeline",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    logger.info(
        f"Scheduler configured: daily job at {settings.POST_HOUR}:00 "
        f"({settings.TIMEZONE})"
    )
    return scheduler
