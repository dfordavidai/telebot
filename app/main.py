"""FootyOracle application entrypoint.

Runs three things together in one process:
  - FastAPI app (health checks + manual trigger endpoints) for Railway
  - Telegram bot (command polling) - in separate thread
  - APScheduler (daily import -> score -> publish job)
"""

import asyncio
import threading
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
bot_thread = None
bot_loop = None


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


def run_bot_polling():
    """Run Telegram bot polling in a separate thread with its own event loop."""
    global telegram_app, bot_loop
    
    try:
        # Create new event loop for this thread
        bot_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(bot_loop)
        
        # Initialize database in this thread
        try:
            db.init_db()
            logger.info("✓ Database initialized (bot thread)")
        except Exception as e:
            logger.error(f"✗ Database init failed in bot thread: {e}")
        
        # Build and start bot
        telegram_app = build_application()
        register_handlers(telegram_app)
        
        # Run the bot polling synchronously
        bot_loop.run_until_complete(telegram_app.initialize())
        bot_loop.run_until_complete(telegram_app.start())
        
        logger.info("✓ Telegram bot polling started")
        
        # Start polling (this blocks until stop is called)
        bot_loop.run_until_complete(telegram_app.updater.start_polling())
        
    except Exception as e:
        logger.error(f"✗ Telegram bot failed: {e}")
    finally:
        # Cleanup on exit
        if bot_loop:
            try:
                if telegram_app:
                    bot_loop.run_until_complete(telegram_app.updater.stop())
                    bot_loop.run_until_complete(telegram_app.stop())
                    bot_loop.run_until_complete(telegram_app.shutdown())
            except Exception as e:
                logger.error(f"Error during bot cleanup: {e}")


async def initialize_services():
    """Initialize services (scheduler) in background."""
    global scheduler
    
    logger.info("Initializing services in background...")
    await asyncio.sleep(0.5)  # Give bot thread time to start
    
    # Initialize and start scheduler
    try:
        scheduler = build_scheduler()
        scheduler.start()
        logger.info("✓ Scheduler started")
    except Exception as e:
        logger.error(f"✗ Scheduler failed: {e}")


startup_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle: start services in background."""
    global startup_task, bot_thread
    
    logger.info("🚀 Starting FootyOracle...")
    
    # Start bot polling in a separate thread
    bot_thread = threading.Thread(target=run_bot_polling, daemon=False)
    bot_thread.start()
    logger.info("Bot polling thread started")
    
    # Schedule scheduler initialization in background
    startup_task = asyncio.create_task(initialize_services())
    
    yield
    
    logger.info("🛑 Shutting down FootyOracle...")
    
    # Cancel startup if still running
    if startup_task and not startup_task.done():
        startup_task.cancel()
        try:
            await startup_task
        except asyncio.CancelledError:
            pass
    
    # Cleanup scheduler
    if scheduler:
        try:
            scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")
    
    # Stop bot polling
    if bot_loop and telegram_app:
        try:
            # Schedule stop in the bot loop
            asyncio.run_coroutine_threadsafe(
                telegram_app.updater.stop(), bot_loop
            ).result(timeout=5)
            asyncio.run_coroutine_threadsafe(
                telegram_app.stop(), bot_loop
            ).result(timeout=5)
            asyncio.run_coroutine_threadsafe(
                telegram_app.shutdown(), bot_loop
            ).result(timeout=5)
            logger.info("Telegram bot shut down")
        except Exception as e:
            logger.error(f"Error shutting down telegram: {e}")
    
    # Wait for bot thread to finish
    if bot_thread and bot_thread.is_alive():
        bot_thread.join(timeout=10)
        logger.info("Bot polling thread stopped")


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
