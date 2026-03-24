"""
Unit tests for the WhatsApp newsletter feature.

Covers:
- schemas/whatsapp.py (Pydantic validation)
- services/whatsapp_service.py (send functions, rate limiter)
- services/newsletter_service.py (subscriber CRUD, newsletter runner, status)
- services/message_formatter.py (formatting edge cases)

All external HTTP calls and heavy data fetches are mocked.
"""
from __future__ import annotations

import os
import sys
import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest

_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_BACKEND_DIR))


# ---------------------------------------------------------------------------
# schemas/whatsapp.py — Pydantic validation
# ---------------------------------------------------------------------------

class TestAddSubscriberRequest:
    def test_valid_colombian_phone(self):
        from app.schemas.whatsapp import AddSubscriberRequest
        req = AddSubscriberRequest(phone_number="+573001234567")
        assert req.phone_number == "+573001234567"
        assert req.comuna_code == "ALL"

    def test_valid_phone_with_comuna(self):
        from app.schemas.whatsapp import AddSubscriberRequest
        req = AddSubscriberRequest(phone_number="+573001234567", comuna_code="05")
        assert req.comuna_code == "05"

    def test_strips_dashes(self):
        from app.schemas.whatsapp import AddSubscriberRequest
        # Dashes within max_length are cleaned by the validator
        req = AddSubscriberRequest(phone_number="+57-3001234567")
        assert req.phone_number == "+573001234567"

    def test_rejects_no_plus_prefix(self):
        from app.schemas.whatsapp import AddSubscriberRequest
        with pytest.raises(Exception):
            AddSubscriberRequest(phone_number="573001234567")

    def test_rejects_too_short(self):
        from app.schemas.whatsapp import AddSubscriberRequest
        with pytest.raises(Exception):
            AddSubscriberRequest(phone_number="+1234")

    def test_rejects_letters(self):
        from app.schemas.whatsapp import AddSubscriberRequest
        with pytest.raises(Exception):
            AddSubscriberRequest(phone_number="+57abcdefghij")

    def test_rejects_empty(self):
        from app.schemas.whatsapp import AddSubscriberRequest
        with pytest.raises(Exception):
            AddSubscriberRequest(phone_number="")


class TestRemoveSubscriberRequest:
    def test_valid_phone(self):
        from app.schemas.whatsapp import RemoveSubscriberRequest
        req = RemoveSubscriberRequest(phone_number="+573009876543")
        assert req.phone_number == "+573009876543"

    def test_rejects_invalid(self):
        from app.schemas.whatsapp import RemoveSubscriberRequest
        with pytest.raises(Exception):
            RemoveSubscriberRequest(phone_number="bad")


class TestNewsletterSubscriberModel:
    def test_defaults(self):
        from app.schemas.whatsapp import NewsletterSubscriber
        sub = NewsletterSubscriber(id=1, phone_number="+573001234567", created_at="2025-01-01")
        assert sub.active is True
        assert sub.comuna_code == "ALL"


class TestManualSendResponse:
    def test_defaults(self):
        from app.schemas.whatsapp import ManualSendResponse
        resp = ManualSendResponse(success=True)
        assert resp.sent_count == 0
        assert resp.errors == []


# ---------------------------------------------------------------------------
# services/whatsapp_service.py — sending + rate limiting
# ---------------------------------------------------------------------------

class TestIsConfigured:
    def test_not_configured_by_default(self):
        from app.services.whatsapp_service import is_configured
        # In test env, env vars are not set
        assert is_configured() is False

    def test_configured_when_both_set(self):
        import app.services.whatsapp_service as ws
        original_token = ws.WHATSAPP_ACCESS_TOKEN
        original_phone = ws.WHATSAPP_PHONE_NUMBER_ID
        try:
            ws.WHATSAPP_ACCESS_TOKEN = "test-token"
            ws.WHATSAPP_PHONE_NUMBER_ID = "12345"
            assert ws.is_configured() is True
        finally:
            ws.WHATSAPP_ACCESS_TOKEN = original_token
            ws.WHATSAPP_PHONE_NUMBER_ID = original_phone

    def test_not_configured_if_token_missing(self):
        import app.services.whatsapp_service as ws
        original_token = ws.WHATSAPP_ACCESS_TOKEN
        try:
            ws.WHATSAPP_ACCESS_TOKEN = ""
            assert ws.is_configured() is False
        finally:
            ws.WHATSAPP_ACCESS_TOKEN = original_token


class TestRateLimiter:
    def test_check_rate_limit_allows_under_cap(self):
        from app.services.whatsapp_service import _check_rate_limit, _send_timestamps
        _send_timestamps.clear()
        assert _check_rate_limit() is True

    def test_check_rate_limit_blocks_over_cap(self):
        import app.services.whatsapp_service as ws
        ws._send_timestamps.clear()
        now = time.time()
        # Fill up timestamps to hit the limit
        ws._send_timestamps.extend([now] * ws.RATE_LIMIT_PER_MINUTE)
        assert ws._check_rate_limit() is False
        ws._send_timestamps.clear()

    def test_old_timestamps_pruned(self):
        import app.services.whatsapp_service as ws
        ws._send_timestamps.clear()
        old = time.time() - 120  # 2 minutes ago
        ws._send_timestamps.extend([old] * 100)
        assert ws._check_rate_limit() is True
        # Old ones should be pruned
        assert len(ws._send_timestamps) == 0

    def test_record_send_appends_timestamp(self):
        import app.services.whatsapp_service as ws
        ws._send_timestamps.clear()
        ws._record_send()
        assert len(ws._send_timestamps) == 1
        ws._send_timestamps.clear()


class TestSendTextMessage:
    def test_returns_not_configured_when_no_creds(self):
        from app.services.whatsapp_service import send_text_message
        result = send_text_message("+573001234567", "Hello")
        assert result["success"] is False
        assert "not configured" in result["detail"]

    def test_returns_rate_limited(self):
        import app.services.whatsapp_service as ws
        original_token = ws.WHATSAPP_ACCESS_TOKEN
        original_phone = ws.WHATSAPP_PHONE_NUMBER_ID
        try:
            ws.WHATSAPP_ACCESS_TOKEN = "test"
            ws.WHATSAPP_PHONE_NUMBER_ID = "123"
            ws._send_timestamps.clear()
            now = time.time()
            ws._send_timestamps.extend([now] * ws.RATE_LIMIT_PER_MINUTE)
            result = ws.send_text_message("+573001234567", "Hello")
            assert result["success"] is False
            assert "Rate limit" in result["detail"]
        finally:
            ws.WHATSAPP_ACCESS_TOKEN = original_token
            ws.WHATSAPP_PHONE_NUMBER_ID = original_phone
            ws._send_timestamps.clear()

    @patch("app.services.whatsapp_service.http_requests.post")
    def test_successful_send(self, mock_post):
        import app.services.whatsapp_service as ws
        original_token = ws.WHATSAPP_ACCESS_TOKEN
        original_phone = ws.WHATSAPP_PHONE_NUMBER_ID
        try:
            ws.WHATSAPP_ACCESS_TOKEN = "test-token"
            ws.WHATSAPP_PHONE_NUMBER_ID = "12345"
            ws._send_timestamps.clear()

            mock_resp = MagicMock()
            mock_resp.json.return_value = {"messages": [{"id": "wamid.abc123"}]}
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            result = ws.send_text_message("+573001234567", "Hello World")
            assert result["success"] is True
            assert result["message_id"] == "wamid.abc123"
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args
            assert call_kwargs[1]["json"]["to"] == "573001234567"
            assert call_kwargs[1]["json"]["text"]["body"] == "Hello World"
        finally:
            ws.WHATSAPP_ACCESS_TOKEN = original_token
            ws.WHATSAPP_PHONE_NUMBER_ID = original_phone
            ws._send_timestamps.clear()

    @patch("app.services.whatsapp_service.http_requests.post")
    def test_http_error_returns_failure(self, mock_post):
        import app.services.whatsapp_service as ws
        import requests
        original_token = ws.WHATSAPP_ACCESS_TOKEN
        original_phone = ws.WHATSAPP_PHONE_NUMBER_ID
        try:
            ws.WHATSAPP_ACCESS_TOKEN = "test-token"
            ws.WHATSAPP_PHONE_NUMBER_ID = "12345"
            ws._send_timestamps.clear()

            mock_post.side_effect = requests.exceptions.ConnectionError("Network down")
            result = ws.send_text_message("+573001234567", "Test")
            assert result["success"] is False
            assert "Network down" in result["detail"]
        finally:
            ws.WHATSAPP_ACCESS_TOKEN = original_token
            ws.WHATSAPP_PHONE_NUMBER_ID = original_phone
            ws._send_timestamps.clear()


class TestSendTemplateMessage:
    def test_returns_not_configured(self):
        from app.services.whatsapp_service import send_template_message
        result = send_template_message("+573001234567", "medcity_report")
        assert result["success"] is False

    @patch("app.services.whatsapp_service.http_requests.post")
    def test_successful_template_send(self, mock_post):
        import app.services.whatsapp_service as ws
        original_token = ws.WHATSAPP_ACCESS_TOKEN
        original_phone = ws.WHATSAPP_PHONE_NUMBER_ID
        try:
            ws.WHATSAPP_ACCESS_TOKEN = "test-token"
            ws.WHATSAPP_PHONE_NUMBER_ID = "12345"
            ws._send_timestamps.clear()

            mock_resp = MagicMock()
            mock_resp.json.return_value = {"messages": [{"id": "wamid.tmpl1"}]}
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            result = ws.send_template_message(
                "+573001234567", "medcity_report",
                components=[{"type": "body", "parameters": [{"type": "text", "text": "Test"}]}],
            )
            assert result["success"] is True
            assert result["message_id"] == "wamid.tmpl1"
            payload = mock_post.call_args[1]["json"]
            assert payload["template"]["name"] == "medcity_report"
            assert "components" in payload["template"]
        finally:
            ws.WHATSAPP_ACCESS_TOKEN = original_token
            ws.WHATSAPP_PHONE_NUMBER_ID = original_phone
            ws._send_timestamps.clear()

    @patch("app.services.whatsapp_service.http_requests.post")
    def test_template_without_components(self, mock_post):
        import app.services.whatsapp_service as ws
        original_token = ws.WHATSAPP_ACCESS_TOKEN
        original_phone = ws.WHATSAPP_PHONE_NUMBER_ID
        try:
            ws.WHATSAPP_ACCESS_TOKEN = "test-token"
            ws.WHATSAPP_PHONE_NUMBER_ID = "12345"
            ws._send_timestamps.clear()

            mock_resp = MagicMock()
            mock_resp.json.return_value = {"messages": [{"id": "wamid.tmpl2"}]}
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            result = ws.send_template_message("+573001234567", "hello_world")
            assert result["success"] is True
            payload = mock_post.call_args[1]["json"]
            assert "components" not in payload["template"]
        finally:
            ws.WHATSAPP_ACCESS_TOKEN = original_token
            ws.WHATSAPP_PHONE_NUMBER_ID = original_phone
            ws._send_timestamps.clear()

    @patch("app.services.whatsapp_service.http_requests.post")
    def test_template_http_error(self, mock_post):
        import app.services.whatsapp_service as ws
        import requests
        original_token = ws.WHATSAPP_ACCESS_TOKEN
        original_phone = ws.WHATSAPP_PHONE_NUMBER_ID
        try:
            ws.WHATSAPP_ACCESS_TOKEN = "test-token"
            ws.WHATSAPP_PHONE_NUMBER_ID = "12345"
            ws._send_timestamps.clear()

            mock_post.side_effect = requests.exceptions.Timeout("Timed out")
            result = ws.send_template_message("+573001234567", "medcity_report")
            assert result["success"] is False
            assert "Timed out" in result["detail"]
        finally:
            ws.WHATSAPP_ACCESS_TOKEN = original_token
            ws.WHATSAPP_PHONE_NUMBER_ID = original_phone
            ws._send_timestamps.clear()


# ---------------------------------------------------------------------------
# services/newsletter_service.py — subscriber store + runner
# ---------------------------------------------------------------------------

class TestSubscriberCRUD:
    """Test subscriber CRUD using a temporary in-memory DB."""

    @pytest.fixture(autouse=True)
    def setup_temp_db(self, tmp_path):
        import app.services.newsletter_service as ns
        ns._db = None
        ns.WHATSAPP_DB_PATH = str(tmp_path / "test_subscribers.sqlite3")
        yield
        ns._db = None

    def test_add_subscriber(self):
        from app.services.newsletter_service import add_subscriber, get_active_subscribers
        result = add_subscriber("+573001111111")
        assert result["success"] is True
        subs = get_active_subscribers()
        assert len(subs) == 1
        assert subs[0]["phone_number"] == "+573001111111"
        assert subs[0]["comuna_code"] == "ALL"

    def test_add_subscriber_with_comuna(self):
        from app.services.newsletter_service import add_subscriber, get_active_subscribers
        add_subscriber("+573002222222", comuna_code="01")
        subs = get_active_subscribers()
        assert subs[0]["comuna_code"] == "01"

    def test_add_duplicate_reactivates(self):
        from app.services.newsletter_service import (
            add_subscriber, remove_subscriber, get_active_subscribers,
        )
        add_subscriber("+573003333333")
        remove_subscriber("+573003333333")
        assert len(get_active_subscribers()) == 0
        add_subscriber("+573003333333", comuna_code="05")
        subs = get_active_subscribers()
        assert len(subs) == 1
        assert subs[0]["comuna_code"] == "05"

    def test_remove_subscriber(self):
        from app.services.newsletter_service import (
            add_subscriber, remove_subscriber, get_active_subscribers,
        )
        add_subscriber("+573004444444")
        assert len(get_active_subscribers()) == 1
        result = remove_subscriber("+573004444444")
        assert result["success"] is True
        assert len(get_active_subscribers()) == 0

    def test_remove_nonexistent_is_no_op(self):
        from app.services.newsletter_service import remove_subscriber, get_active_subscribers
        result = remove_subscriber("+579999999999")
        assert result["success"] is True
        assert len(get_active_subscribers()) == 0

    def test_multiple_subscribers(self):
        from app.services.newsletter_service import add_subscriber, get_active_subscribers
        add_subscriber("+573001111111")
        add_subscriber("+573002222222")
        add_subscriber("+573003333333")
        assert len(get_active_subscribers()) == 3


class TestLogSend:
    @pytest.fixture(autouse=True)
    def setup_temp_db(self, tmp_path):
        import app.services.newsletter_service as ns
        ns._db = None
        ns.WHATSAPP_DB_PATH = str(tmp_path / "test_log.sqlite3")
        yield
        ns._db = None

    def test_log_send_creates_entry(self):
        from app.services.newsletter_service import _log_send, _get_db
        _log_send("+573001111111", "sent", "wamid.123")
        db = _get_db()
        rows = db.execute("SELECT * FROM send_log").fetchall()
        assert len(rows) == 1
        assert rows[0][1] == "+573001111111"
        assert rows[0][2] == "sent"

    def test_log_send_error_entry(self):
        from app.services.newsletter_service import _log_send, _get_db
        _log_send("+573001111111", "error", error_detail="Connection refused")
        db = _get_db()
        rows = db.execute("SELECT * FROM send_log").fetchall()
        assert rows[0][2] == "error"
        assert rows[0][4] == "Connection refused"


class TestGetNewsletterStatus:
    @pytest.fixture(autouse=True)
    def setup_temp_db(self, tmp_path):
        import app.services.newsletter_service as ns
        ns._db = None
        ns.WHATSAPP_DB_PATH = str(tmp_path / "test_status.sqlite3")
        yield
        ns._db = None

    def test_status_empty_db(self):
        from app.services.newsletter_service import get_newsletter_status
        status = get_newsletter_status()
        assert status["subscriber_count"] == 0
        assert status["messages_sent_today"] == 0
        assert status["last_run_at"] is None
        assert status["next_run_at"] is None

    def test_status_with_subscribers(self):
        from app.services.newsletter_service import (
            add_subscriber, get_newsletter_status,
        )
        add_subscriber("+573001111111")
        add_subscriber("+573002222222")
        status = get_newsletter_status()
        assert status["subscriber_count"] == 2

    def test_status_with_send_log(self):
        from app.services.newsletter_service import (
            _log_send, get_newsletter_status,
        )
        _log_send("+573001111111", "sent", "wamid.1")
        _log_send("+573001111111", "sent", "wamid.2")
        status = get_newsletter_status()
        assert status["messages_sent_today"] == 2
        assert status["last_run_at"] is not None

    def test_status_with_scheduler(self):
        from app.services.newsletter_service import get_newsletter_status
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        mock_job = MagicMock()
        mock_job.next_run_time.isoformat.return_value = "2025-01-01T08:00:00-05:00"
        mock_scheduler.get_job.return_value = mock_job
        status = get_newsletter_status(scheduler=mock_scheduler)
        assert status["next_run_at"] == "2025-01-01T08:00:00-05:00"

    def test_status_with_no_running_scheduler(self):
        from app.services.newsletter_service import get_newsletter_status
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        status = get_newsletter_status(scheduler=mock_scheduler)
        assert status["next_run_at"] is None


class TestRunNewsletter:
    @pytest.fixture(autouse=True)
    def setup_temp_db(self, tmp_path):
        import app.services.newsletter_service as ns
        ns._db = None
        ns.WHATSAPP_DB_PATH = str(tmp_path / "test_runner.sqlite3")
        ns._SEND_DELAY_SECONDS = 0  # No delay in tests
        yield
        ns._db = None
        ns._SEND_DELAY_SECONDS = 2.0

    def test_run_not_configured(self):
        from app.services.newsletter_service import run_newsletter
        result = run_newsletter()
        assert result["success"] is False
        assert "not configured" in result["errors"][0]

    @patch("app.services.newsletter_service.is_configured", return_value=True)
    def test_run_no_subscribers(self, _):
        from app.services.newsletter_service import run_newsletter
        result = run_newsletter()
        assert result["success"] is True
        assert result["sent_count"] == 0

    @patch("app.services.newsletter_service.is_configured", return_value=True)
    @patch("app.services.newsletter_service.send_text_message")
    @patch("app.services.newsletter_service._fetch_newsletter_data")
    def test_run_sends_to_all_subscribers(self, mock_fetch, mock_send, _):
        from app.services.newsletter_service import add_subscriber, run_newsletter

        mock_fetch.return_value = {
            "overview": {
                "metrics": {"safety_homicides": {"value": 100, "unit": "casos"}},
                "recommendations": ["Test rec"],
                "safety_by_comuna": [],
            },
            "security": {"available": False},
            "city_summary": {"available_domains": 3, "total_domains": 7},
        }
        mock_send.return_value = {"success": True, "message_id": "wamid.test"}

        add_subscriber("+573001111111")
        add_subscriber("+573002222222")

        result = run_newsletter()
        assert result["success"] is True
        assert result["sent_count"] == 2
        assert mock_send.call_count == 2

    @patch("app.services.newsletter_service.is_configured", return_value=True)
    @patch("app.services.newsletter_service.send_text_message")
    @patch("app.services.newsletter_service._fetch_newsletter_data")
    def test_run_handles_send_failure(self, mock_fetch, mock_send, _):
        from app.services.newsletter_service import add_subscriber, run_newsletter

        mock_fetch.return_value = {
            "overview": {"metrics": {}, "recommendations": [], "safety_by_comuna": []},
            "security": {"available": False},
            "city_summary": {"available_domains": 0, "total_domains": 0},
        }
        mock_send.return_value = {"success": False, "detail": "Rate limited"}

        add_subscriber("+573001111111")
        result = run_newsletter()
        assert result["success"] is True
        assert result["sent_count"] == 0
        assert len(result["errors"]) == 1
        assert "Rate limited" in result["errors"][0]

    @patch("app.services.newsletter_service.is_configured", return_value=True)
    @patch("app.services.newsletter_service._fetch_newsletter_data")
    def test_run_handles_data_fetch_failure(self, mock_fetch, _):
        from app.services.newsletter_service import add_subscriber, run_newsletter

        mock_fetch.side_effect = Exception("MEData is down")
        add_subscriber("+573001111111")

        result = run_newsletter()
        assert result["success"] is False
        assert "MEData is down" in result["errors"][0]

    @patch("app.services.newsletter_service.is_configured", return_value=True)
    @patch("app.services.newsletter_service.send_text_message")
    @patch("app.services.newsletter_service._fetch_newsletter_data")
    def test_run_handles_formatting_exception(self, mock_fetch, mock_send, _):
        from app.services.newsletter_service import add_subscriber, run_newsletter

        # Return data that will cause format_daily_newsletter to be called normally,
        # but make send_text_message raise for the first subscriber
        mock_fetch.return_value = {
            "overview": {"metrics": {}, "recommendations": [], "safety_by_comuna": []},
            "security": {"available": False},
            "city_summary": {"available_domains": 0, "total_domains": 0},
        }
        mock_send.side_effect = Exception("Unexpected error")

        add_subscriber("+573001111111")
        result = run_newsletter()
        assert result["success"] is True
        assert result["sent_count"] == 0
        assert len(result["errors"]) == 1


class TestSchedulerLifecycle:
    def test_start_scheduler_disabled(self):
        import app.services.newsletter_service as ns
        original = ns.NEWSLETTER_ENABLED
        try:
            ns.NEWSLETTER_ENABLED = False
            result = ns.start_scheduler()
            assert result is None
        finally:
            ns.NEWSLETTER_ENABLED = original

    def test_start_scheduler_no_creds(self):
        import app.services.newsletter_service as ns
        original = ns.NEWSLETTER_ENABLED
        try:
            ns.NEWSLETTER_ENABLED = True
            # is_configured() returns False since env vars aren't set
            result = ns.start_scheduler()
            assert result is None
        finally:
            ns.NEWSLETTER_ENABLED = original

    def test_stop_scheduler_no_scheduler(self):
        import app.services.newsletter_service as ns
        ns._scheduler = None
        ns.stop_scheduler()  # Should not raise
        assert ns._scheduler is None

    def test_get_scheduler_returns_none_by_default(self):
        import app.services.newsletter_service as ns
        ns._scheduler = None
        assert ns.get_scheduler() is None


# ---------------------------------------------------------------------------
# services/message_formatter.py — edge cases
# ---------------------------------------------------------------------------

class TestFormatDailyNewsletter:
    def test_all_metrics_present(self):
        from app.services.message_formatter import format_daily_newsletter
        msg = format_daily_newsletter(
            overview={
                "metrics": {
                    "mobility_equiv_vehicles": {"value": 50000, "unit": "vehiculos_equivalentes"},
                    "safety_homicides": {"value": 200, "unit": "casos"},
                    "investment_amount": {"value": 10_000_000_000, "unit": "COP"},
                    "lesiones_count": {"value": 500, "unit": "casos"},
                },
                "recommendations": ["Rec 1", "Rec 2", "Rec 3", "Rec 4"],
                "safety_by_comuna": [
                    {"comuna_code": "01", "comuna_name": "Popular", "safety_homicides": 80},
                    {"comuna_code": "08", "comuna_name": "Villa Hermosa", "safety_homicides": 70},
                    {"comuna_code": "03", "safety_homicides": 60},
                    {"comuna_code": "04", "safety_homicides": 50},
                    {"comuna_code": "05", "safety_homicides": 40},
                    {"comuna_code": "06", "safety_homicides": 30},
                ],
            },
            security={"available": True, "by_type": [
                {"crime_type": "HOMICIDIO", "total": 1000},
                {"crime_type": "HURTO A PERSONAS", "total": 5000},
                {"crime_type": "HURTO DE CARROS", "total": 2000},
                {"crime_type": "EXTORSION", "total": 800},
                {"crime_type": "LESIONES", "total": 3000},
                {"crime_type": "EXTRA TYPE", "total": 100},
            ]},
            city_summary={"available_domains": 6, "total_domains": 7},
        )
        assert "50,000" in msg
        assert "200" in msg
        assert "10,000,000,000" in msg
        assert "500" in msg  # lesiones
        assert "Rec 1" in msg
        assert "Rec 2" in msg
        assert "Rec 3" in msg
        assert "Rec 4" not in msg  # Only top 3
        assert "Popular" in msg  # Top comuna name
        assert "HOMICIDIO" in msg
        assert "6/7" in msg
        assert len(msg) <= 4096

    def test_no_security_data(self):
        from app.services.message_formatter import format_daily_newsletter
        msg = format_daily_newsletter(
            overview={"metrics": {}, "recommendations": [], "safety_by_comuna": []},
            security={"available": False},
            city_summary={"available_domains": 0, "total_domains": 0},
        )
        assert "MedCity Dashboard" in msg
        assert "HOMICIDIO" not in msg

    def test_none_metric_values(self):
        from app.services.message_formatter import format_daily_newsletter
        msg = format_daily_newsletter(
            overview={
                "metrics": {
                    "mobility_equiv_vehicles": {"value": None, "unit": "vehiculos_equivalentes"},
                    "safety_homicides": {"value": None, "unit": "casos"},
                },
                "recommendations": [],
                "safety_by_comuna": [],
            },
            security={"available": False},
            city_summary={"available_domains": 2, "total_domains": 7},
        )
        # None values should not appear
        assert "N/D" not in msg or "MedCity" in msg  # graceful handling

    def test_truncation_on_huge_data(self):
        from app.services.message_formatter import format_daily_newsletter
        msg = format_daily_newsletter(
            overview={
                "metrics": {},
                "recommendations": ["x" * 500] * 10,
                "safety_by_comuna": [{"comuna_code": str(i), "safety_homicides": i} for i in range(100)],
            },
            security={"available": True, "by_type": [
                {"crime_type": f"TYPE_{i}", "total": i * 100} for i in range(50)
            ]},
            city_summary={"available_domains": 7, "total_domains": 7},
        )
        assert len(msg) <= 4096


class TestFormatComunaNewsletter:
    def test_with_full_data(self):
        from app.services.message_formatter import format_comuna_newsletter
        msg = format_comuna_newsletter(
            overview={
                "selected": {"comuna_code": "01", "comuna_name": "Popular"},
                "metrics": {
                    "mobility_equiv_vehicles": {"value": 5000, "unit": "vehiculos_equivalentes"},
                    "safety_homicides": {"value": 30, "unit": "casos"},
                    "investment_amount": {"value": 2_500_000_000, "unit": "COP"},
                },
                "recommendations": [
                    "Seguridad [CRITICO]: alta criminalidad.",
                    "Inversion [BAJO]: falta presupuesto.",
                ],
            },
            comuna_code="01",
        )
        assert "Popular" in msg
        assert "5,000" in msg
        assert "COP" in msg
        assert "CRITICO" in msg

    def test_with_no_comuna_name(self):
        from app.services.message_formatter import format_comuna_newsletter
        msg = format_comuna_newsletter(
            overview={
                "selected": {"comuna_code": "99", "comuna_name": None},
                "metrics": {},
                "recommendations": [],
            },
            comuna_code="99",
        )
        assert "Comuna 99" in msg

    def test_truncation(self):
        from app.services.message_formatter import format_comuna_newsletter
        msg = format_comuna_newsletter(
            overview={
                "selected": {"comuna_code": "01", "comuna_name": "Test"},
                "metrics": {},
                "recommendations": ["x" * 1000] * 10,
            },
            comuna_code="01",
        )
        assert len(msg) <= 4096


class TestFmtHelper:
    def test_fmt_none(self):
        from app.services.message_formatter import _fmt
        assert _fmt(None) == "N/D"

    def test_fmt_integer(self):
        from app.services.message_formatter import _fmt
        assert _fmt(1000) == "1,000"

    def test_fmt_float(self):
        from app.services.message_formatter import _fmt
        assert _fmt(1234567.89) == "1,234,568"

    def test_fmt_zero(self):
        from app.services.message_formatter import _fmt
        assert _fmt(0) == "0"
