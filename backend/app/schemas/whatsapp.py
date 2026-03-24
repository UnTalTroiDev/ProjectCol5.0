"""Pydantic schemas for the WhatsApp daily-newsletter feature."""
from __future__ import annotations

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Validators ────────────────────────────────────────────────────────────

_E164_RE = re.compile(r"^\+\d{10,15}$")


def _clean_phone(v: str) -> str:
    v = v.strip().replace(" ", "").replace("-", "")
    if not _E164_RE.match(v):
        raise ValueError("Phone number must be E.164 format (e.g. +573001234567).")
    return v


# ── Subscriber management ────────────────────────────────────────────────

class AddSubscriberRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=16)
    comuna_code: str = Field(default="ALL", max_length=10)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _clean_phone(v)


class RemoveSubscriberRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=16)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return _clean_phone(v)


class NewsletterSubscriber(BaseModel):
    id: int
    phone_number: str
    comuna_code: str = "ALL"
    active: bool = True
    created_at: str


# ── Status / responses ───────────────────────────────────────────────────

class NewsletterStatusResponse(BaseModel):
    configured: bool
    enabled: bool
    subscriber_count: int
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None
    messages_sent_today: int = 0


class ManualSendResponse(BaseModel):
    success: bool
    sent_count: int = 0
    errors: List[str] = []
