"""FootyOracle application entrypoint.

Runs three things together in one process:
  - FastAPI app (health checks + manual trigger endpoints) for Railway
  - Telegram bot (command polling)
  - APScheduler (daily import -> score -> publish job)
"""

import asyncio
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from telegram.ext import CommandHandler

from app.core.config import get_settings
from app.core.logger import get_logger
from app.storage.database import db
from app.api.routes import router
from app.bot.telegram import build_application
from app.bot.commands import (
    start,
    help_command,
    today,
    safe,
    value,
    results,
    stats,
    roi_command,
    month,
    history,
)
from app.jobs.scheduler import build_scheduler

logger = get_logger(__name__)

telegram_app = None
scheduler = None


def register_handlers(application) -> None:
    """Register all Telegram command handlers."""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("safe", safe))
    application.add_handler(CommandHandler("value", value))
    application.add_handler(CommandHandler("results", results))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("roi", roi_command))
    application.add_handler(CommandHandler("month", month))
    application.add_handler(CommandHandler("history", history))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle: init DB, start bot polling, start scheduler."""
    global telegram_app, scheduler

    logger.info("Starting FootyOracle...")

    # Initialize database tables
    db.init_db()

    # Set up and start the Telegram bot
    telegram_app = build_application()
    register_handlers(telegram_app)
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    logger.info("Telegram bot polling started")

    # Set up and start the scheduler
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

    yield

    logger.info("Shutting down FootyOracle...")
    if scheduler:
        scheduler.shutdown(wait=False)
    if telegram_app:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()


app = FastAPI(title="FootyOracle", lifespan=lifespan)
app.include_router(router)


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )
