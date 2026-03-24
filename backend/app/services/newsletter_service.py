"""
Daily newsletter scheduler and subscriber management.

- Stores subscribers in a SQLite database (same volume as the stale cache).
- Uses APScheduler to fire the newsletter daily at a configurable hour.
- Pulls live data from existing dashboard/security/city services and formats
  it via ``message_formatter``, then sends via ``whatsapp_service``.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .whatsapp_service import is_configured, send_text_message
from .message_formatter import format_daily_newsletter, format_comuna_newsletter

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────

WHATSAPP_DB_PATH = os.getenv("WHATSAPP_DB", "/tmp/whatsapp_subscribers.sqlite3")
NEWSLETTER_ENABLED = os.getenv("NEWSLETTER_ENABLED", "false").lower() in ("true", "1", "yes")
NEWSLETTER_SCHEDULE_HOUR = int(os.getenv("NEWSLETTER_SCHEDULE_HOUR", "8"))
NEWSLETTER_TIMEZONE = os.getenv("NEWSLETTER_TIMEZONE", "America/Bogota")

# Delay between messages in seconds (respects rate limits).
_SEND_DELAY_SECONDS = 2.0

# ── SQLite subscriber store ──────────────────────────────────────────────

_db: Optional[sqlite3.Connection] = None


def _get_db() -> sqlite3.Connection:
    global _db
    if _db is None:
        _db = sqlite3.connect(WHATSAPP_DB_PATH, check_same_thread=False)
        _db.execute("PRAGMA journal_mode=WAL")
        _db.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL UNIQUE,
                comuna_code  TEXT NOT NULL DEFAULT 'ALL',
                active       INTEGER NOT NULL DEFAULT 1,
                created_at   TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        _db.execute("""
            CREATE TABLE IF NOT EXISTS send_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'sent',
                message_id   TEXT,
                error_detail TEXT,
                sent_at      TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        _db.commit()
    return _db


# ── Subscriber CRUD ──────────────────────────────────────────────────────

def add_subscriber(phone_number: str, comuna_code: str = "ALL") -> Dict[str, Any]:
    db = _get_db()
    db.execute(
        """INSERT INTO subscribers (phone_number, comuna_code)
           VALUES (?, ?)
           ON CONFLICT(phone_number) DO UPDATE SET
             comuna_code = excluded.comuna_code,
             active = 1,
             updated_at = datetime('now')""",
        (phone_number, comuna_code),
    )
    db.commit()
    return {"success": True, "detail": f"Subscribed {phone_number}."}


def remove_subscriber(phone_number: str) -> Dict[str, Any]:
    db = _get_db()
    db.execute(
        "UPDATE subscribers SET active=0, updated_at=datetime('now') WHERE phone_number=?",
        (phone_number,),
    )
    db.commit()
    return {"success": True, "detail": f"Unsubscribed {phone_number}."}


def get_active_subscribers() -> List[Dict[str, Any]]:
    db = _get_db()
    rows = db.execute(
        "SELECT id, phone_number, comuna_code, created_at FROM subscribers WHERE active=1"
    ).fetchall()
    return [
        {"id": r[0], "phone_number": r[1], "comuna_code": r[2], "created_at": r[3]}
        for r in rows
    ]


def _log_send(
    phone: str, status: str,
    message_id: Optional[str] = None, error_detail: Optional[str] = None,
) -> None:
    try:
        db = _get_db()
        db.execute(
            "INSERT INTO send_log (phone_number, status, message_id, error_detail) VALUES (?, ?, ?, ?)",
            (phone, status, message_id, error_detail),
        )
        db.commit()
    except Exception as exc:
        logger.warning("Failed to log send: %s", exc)


# ── Newsletter runner ─────────────────────────────────────────────────────

def _fetch_newsletter_data() -> Dict[str, Any]:
    """Fetch fresh data from existing services for the newsletter."""
    # Import here to avoid circular imports (services → main → services).
    from .dashboard_service import get_dashboard_overview
    from .security_service import get_criminalidad_consolidada

    overview_resp = get_dashboard_overview(comuna_code="ALL")
    overview_data = overview_resp.model_dump()

    try:
        security_data = get_criminalidad_consolidada()
    except Exception as exc:
        logger.warning("Could not fetch security data for newsletter: %s", exc)
        security_data = {"available": False}

    # Build a lightweight city summary inline (avoid importing main.py's function).
    city_summary_data: Dict[str, Any] = {
        "available_domains": 0,
        "total_domains": 7,
    }
    # Count domains that succeeded in overview.
    if overview_data.get("metrics"):
        city_summary_data["available_domains"] = len(overview_data["metrics"])

    return {
        "overview": overview_data,
        "security": security_data,
        "city_summary": city_summary_data,
    }


def run_newsletter() -> Dict[str, Any]:
    """
    Execute the daily newsletter: fetch data, format, send to all active subscribers.
    Returns a summary dict with sent_count and errors.
    """
    logger.info("Newsletter run started.")

    if not is_configured():
        logger.warning("Newsletter skipped — WhatsApp not configured.")
        return {"success": False, "sent_count": 0, "errors": ["WhatsApp not configured."]}

    subscribers = get_active_subscribers()
    if not subscribers:
        logger.info("Newsletter skipped — no active subscribers.")
        return {"success": True, "sent_count": 0, "errors": []}

    # Fetch data once for all subscribers.
    try:
        data = _fetch_newsletter_data()
    except Exception as exc:
        logger.error("Newsletter data fetch failed: %s", exc)
        return {"success": False, "sent_count": 0, "errors": [str(exc)]}

    sent_count = 0
    errors: List[str] = []

    for sub in subscribers:
        phone = sub["phone_number"]
        comuna = sub["comuna_code"]

        try:
            if comuna == "ALL":
                text = format_daily_newsletter(
                    data["overview"], data["security"], data["city_summary"],
                )
            else:
                # Fetch specific comuna overview for per-comuna subscribers.
                from .dashboard_service import get_dashboard_overview
                comuna_overview = get_dashboard_overview(comuna_code=comuna).model_dump()
                text = format_comuna_newsletter(comuna_overview, comuna)

            result = send_text_message(phone, text)

            if result.get("success"):
                sent_count += 1
                _log_send(phone, "sent", result.get("message_id"))
            else:
                err = f"{phone}: {result.get('detail', 'unknown error')}"
                errors.append(err)
                _log_send(phone, "error", error_detail=result.get("detail"))

        except Exception as exc:
            err = f"{phone}: {exc}"
            errors.append(err)
            _log_send(phone, "error", error_detail=str(exc))

        # Small delay to respect rate limits.
        time.sleep(_SEND_DELAY_SECONDS)

    logger.info("Newsletter done: sent=%d errors=%d", sent_count, len(errors))
    return {"success": True, "sent_count": sent_count, "errors": errors}


# ── Status ────────────────────────────────────────────────────────────────

def get_newsletter_status(scheduler: Optional[BackgroundScheduler] = None) -> Dict[str, Any]:
    db = _get_db()

    sub_count = db.execute(
        "SELECT COUNT(*) FROM subscribers WHERE active=1"
    ).fetchone()[0]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sent_today = db.execute(
        "SELECT COUNT(*) FROM send_log WHERE sent_at LIKE ? AND status='sent'",
        (f"{today}%",),
    ).fetchone()[0]

    last_send = db.execute(
        "SELECT sent_at FROM send_log WHERE status='sent' ORDER BY id DESC LIMIT 1"
    ).fetchone()

    next_run: Optional[str] = None
    if scheduler and scheduler.running:
        job = scheduler.get_job("daily_newsletter")
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()

    return {
        "configured": is_configured(),
        "enabled": NEWSLETTER_ENABLED,
        "subscriber_count": sub_count,
        "next_run_at": next_run,
        "last_run_at": last_send[0] if last_send else None,
        "messages_sent_today": sent_today,
    }


# ── Scheduler lifecycle ──────────────────────────────────────────────────

_scheduler: Optional[BackgroundScheduler] = None


def start_scheduler() -> Optional[BackgroundScheduler]:
    """Start the background scheduler if newsletter is enabled."""
    global _scheduler

    if not NEWSLETTER_ENABLED:
        logger.info("Newsletter scheduler disabled (NEWSLETTER_ENABLED != true).")
        return None

    if not is_configured():
        logger.warning("Newsletter scheduler not started — WhatsApp credentials missing.")
        return None

    _scheduler = BackgroundScheduler(daemon=True)
    trigger = CronTrigger(
        hour=NEWSLETTER_SCHEDULE_HOUR,
        minute=0,
        timezone=NEWSLETTER_TIMEZONE,
    )
    _scheduler.add_job(run_newsletter, trigger, id="daily_newsletter", replace_existing=True)
    _scheduler.start()
    logger.info(
        "Newsletter scheduler started — daily at %02d:00 %s",
        NEWSLETTER_SCHEDULE_HOUR,
        NEWSLETTER_TIMEZONE,
    )
    return _scheduler


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Newsletter scheduler stopped.")
    _scheduler = None


def get_scheduler() -> Optional[BackgroundScheduler]:
    return _scheduler
