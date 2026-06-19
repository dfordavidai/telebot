"""Telegram bot instance, message formatting, and send helpers."""

from typing import List, Dict, Optional
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application
from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)

CATEGORY_EMOJI = {
    "SAFE": "🟢",
    "VALUE": "🟡",
    "HIGH_RISK": "🔴",
}

CATEGORY_LABEL = {
    "SAFE": "SAFE",
    "VALUE": "VALUE",
    "HIGH_RISK": "HIGH RISK",
}


def build_application() -> Application:
    """Build the python-telegram-bot Application instance."""
    settings = get_settings()
    return Application.builder().token(settings.BOT_TOKEN).build()


def get_bot() -> Bot:
    """Get a standalone Bot instance for one-off sends (e.g. from the scheduler)."""
    settings = get_settings()
    return Bot(token=settings.BOT_TOKEN)


def format_daily_sheet(picks: List[Dict], roi_30d: Optional[Dict] = None) -> str:
    """
    Format the daily picks sheet for Telegram, grouped by category.

    `picks` items expected shape:
        {"home": str, "away": str, "pick": str, "confidence": int, "category": str}
    """
    if not picks:
        return "🔥 *DAILY SHEET*\n\nNo qualifying picks today. Check back tomorrow."

    lines = ["🔥 *DAILY SHEET*", ""]

    grouped: Dict[str, List[Dict]] = {"SAFE": [], "VALUE": [], "HIGH_RISK": []}
    for p in picks:
        grouped.setdefault(p["category"], []).append(p)

    section_order = ["SAFE", "VALUE", "HIGH_RISK"]
    first_section = True

    for category in section_order:
        items = grouped.get(category, [])
        if not items:
            continue

        if not first_section:
            lines.append("————————")
        first_section = False

        emoji = CATEGORY_EMOJI.get(category, "⚪")
        label = CATEGORY_LABEL.get(category, category)
        lines.append(f"{emoji} *{label}*")
        lines.append("")

        for item in items:
            lines.append(f"⚽ {item['home']} vs {item['away']}")
            lines.append(f"Market: {item['pick']}")
            lines.append(f"Confidence: {item['confidence']}")
            lines.append("")

    if roi_30d:
        lines.append("————————")
        lines.append(f"Month ROI: {roi_30d.get('roi_percent', 0):+.1f}%")

    return "\n".join(lines).strip()


async def send_message(text: str, chat_id: Optional[str] = None) -> bool:
    """Send a message to the configured chat (or an override chat_id)."""
    settings = get_settings()
    target = chat_id or settings.CHAT_ID
    bot = get_bot()

    try:
        await bot.send_message(
            chat_id=target,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
        return True
    except TelegramError as e:
        logger.error(f"Telegram send failed: {e}")
        return False
