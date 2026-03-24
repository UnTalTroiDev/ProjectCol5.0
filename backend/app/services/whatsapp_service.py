"""
WhatsApp Business Cloud API sending service.

Sends text and template messages via Meta's Graph API.
All calls use the existing `requests` library — no extra SDK needed.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests as http_requests

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0"
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
RATE_LIMIT_PER_MINUTE = int(os.getenv("WHATSAPP_RATE_LIMIT_PER_MINUTE", "30"))

# Simple in-memory sliding-window rate limiter.
_send_timestamps: List[float] = []


def is_configured() -> bool:
    """Return True if the required WhatsApp credentials are set."""
    return bool(WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID)


# ── Rate limiting ─────────────────────────────────────────────────────────

def _check_rate_limit() -> bool:
    """Return True if we can send (under the per-minute cap)."""
    now = time.time()
    cutoff = now - 60
    _send_timestamps[:] = [t for t in _send_timestamps if t > cutoff]
    return len(_send_timestamps) < RATE_LIMIT_PER_MINUTE


def _record_send() -> None:
    _send_timestamps.append(time.time())


# ── Sending ───────────────────────────────────────────────────────────────

def send_text_message(phone_number: str, text: str) -> Dict[str, Any]:
    """
    Send a plain text message via the WhatsApp Cloud API.

    For users who have *not* messaged the business number in the last 24 h,
    this will fail — use ``send_template_message`` to initiate the conversation.
    """
    if not is_configured():
        return {"success": False, "detail": "WhatsApp not configured."}

    if not _check_rate_limit():
        return {"success": False, "detail": "Rate limit exceeded. Try again shortly."}

    url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number.lstrip("+"),
        "type": "text",
        "text": {"body": text},
    }

    try:
        resp = http_requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        message_id = data.get("messages", [{}])[0].get("id", "")
        _record_send()
        logger.info("WhatsApp text sent to %s — id=%s", phone_number, message_id)
        return {"success": True, "message_id": message_id, "detail": "Message sent."}
    except http_requests.exceptions.RequestException as exc:
        detail = str(exc)
        logger.error("WhatsApp send to %s failed: %s", phone_number, detail)
        return {"success": False, "message_id": None, "detail": detail}


def send_template_message(
    phone_number: str,
    template_name: str,
    language_code: str = "es",
    components: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Send a pre-approved template message (required to initiate conversations
    outside the 24-hour window).
    """
    if not is_configured():
        return {"success": False, "detail": "WhatsApp not configured."}

    if not _check_rate_limit():
        return {"success": False, "detail": "Rate limit exceeded."}

    url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    template_obj: Dict[str, Any] = {
        "name": template_name,
        "language": {"code": language_code},
    }
    if components:
        template_obj["components"] = components

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number.lstrip("+"),
        "type": "template",
        "template": template_obj,
    }

    try:
        resp = http_requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        message_id = data.get("messages", [{}])[0].get("id", "")
        _record_send()
        logger.info("WhatsApp template '%s' sent to %s — id=%s", template_name, phone_number, message_id)
        return {"success": True, "message_id": message_id, "detail": "Template sent."}
    except http_requests.exceptions.RequestException as exc:
        detail = str(exc)
        logger.error("WhatsApp template send to %s failed: %s", phone_number, detail)
        return {"success": False, "message_id": None, "detail": detail}
