"""Entry point for the MedCity Telegram bot.

Usage:
    python bot_runner.py

Requires TELEGRAM_BOT_TOKEN environment variable.
"""

import logging

from app.bot.telegram_bot import create_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    bot = create_bot()
    logging.getLogger(__name__).info("Starting MedCity Telegram bot (polling)…")
    bot.run_polling()
