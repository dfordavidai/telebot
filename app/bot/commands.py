"""Telegram command handlers."""

from datetime import datetime
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from app.core.logger import get_logger
from app.storage.database import db
from app.models.match import Prediction
from app.bot.telegram import format_daily_sheet, CATEGORY_EMOJI
from app.services.roi import ROITracker

logger = get_logger(__name__)

HELP_TEXT = (
    "🔥 *FootyOracle Commands*\n\n"
    "/today — full daily sheet\n"
    "/safe — SAFE picks only\n"
    "/value — VALUE picks only\n"
    "/results — recent settled results\n"
    "/stats — last 30 days performance\n"
    "/roi — current ROI summary\n"
    "/month — this month's stats\n"
    "/history — last 10 picks\n"
    "/help — show this message"
)


def _today_predictions(category: str = None):
    session = db.get_session()
    try:
        today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        today_end = datetime.combine(datetime.utcnow().date(), datetime.max.time())

        query = session.query(Prediction).join(Prediction.match).filter(
            Prediction.posted_at >= today_start,
            Prediction.posted_at <= today_end,
        )
        if category:
            query = query.filter(Prediction.category == category)

        predictions = query.all()
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
    finally:
        session.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start."""
    await update.message.reply_text(
        "Welcome to FootyOracle ⚽\n\nDaily betting intelligence, automatically scored and filtered.\n\n"
        + HELP_TEXT,
        parse_mode=ParseMode.MARKDOWN,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help."""
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /today — full daily sheet."""
    picks = _today_predictions()
    session = db.get_session()
    try:
        roi_30d = ROITracker.calculate_roi(session, days=30)
    finally:
        session.close()
    await update.message.reply_text(
        format_daily_sheet(picks, roi_30d), parse_mode=ParseMode.MARKDOWN
    )


async def safe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /safe — SAFE category picks only."""
    picks = _today_predictions(category="SAFE")
    await update.message.reply_text(
        format_daily_sheet(picks), parse_mode=ParseMode.MARKDOWN
    )


async def value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /value — VALUE category picks only."""
    picks = _today_predictions(category="VALUE")
    await update.message.reply_text(
        format_daily_sheet(picks), parse_mode=ParseMode.MARKDOWN
    )


async def results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /results — recent settled results."""
    session = db.get_session()
    try:
        recent = ROITracker.get_recent_results(session, limit=10)
    finally:
        session.close()

    if not recent:
        await update.message.reply_text("No settled results yet.")
        return

    lines = ["📊 *Recent Results*", ""]
    for r in recent:
        outcome = "✅" if r["result"] == "WON" else ("❌" if r["result"] == "LOST" else "➖")
        lines.append(f"{outcome} {r['match']} — {r['pick']} ({r['confidence']})")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats — last 30 days performance."""
    session = db.get_session()
    try:
        metrics = ROITracker.calculate_roi(session, days=30)
    finally:
        session.close()

    text = (
        "📈 *30-Day Stats*\n\n"
        f"Picks: {metrics['total_picks']}\n"
        f"Wins: {metrics['wins']}  Losses: {metrics['losses']}\n"
        f"Win rate: {metrics['win_rate']}%\n"
        f"Profit: {metrics['profit']:+.2f}u\n"
        f"ROI: {metrics['roi_percent']:+.1f}%\n"
        f"Avg confidence: {metrics['avg_confidence']}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def roi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /roi — current ROI summary (30 days)."""
    await stats(update, context)


async def month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /month — current month's stats."""
    now = datetime.utcnow()
    session = db.get_session()
    try:
        metrics = ROITracker.monthly_stats(session, now.year, now.month)
    finally:
        session.close()

    text = (
        f"📅 *{metrics['month']}*\n\n"
        f"Picks: {metrics['picks']}\n"
        f"Wins: {metrics['wins']}  Losses: {metrics['losses']}\n"
        f"Win rate: {metrics['win_rate']}%\n"
        f"Profit: {metrics['profit']:+.2f}u"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /history — last 10 picks regardless of settled status."""
    session = db.get_session()
    try:
        recent = ROITracker.get_recent_results(session, limit=10)
    finally:
        session.close()

    if not recent:
        await update.message.reply_text("No pick history yet.")
        return

    lines = ["🗂 *Pick History*", ""]
    for r in recent:
        emoji = CATEGORY_EMOJI.get(r.get("category", ""), "⚪")
        lines.append(f"{emoji} {r['match']} — {r['pick']} ({r['confidence']}) [{r['result']}]")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
