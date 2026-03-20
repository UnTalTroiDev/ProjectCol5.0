"""
Integration tests for the MedCity Dashboard API.

These tests use FastAPI's TestClient (backed by httpx) which runs the full
ASGI app in-process — no network required, no mocks.  The service layer does
make outbound HTTP requests to MEData (medata.gov.co) to fetch CSVs on the
first call; subsequent calls are served from the TTL cache.

Run from the repository root:
    pytest backend/tests/

Requirements:
    pip install pytest httpx
    (Both are listed in backend/requirements.txt)
"""
from __future__ import annotations

import sys
import os

# ---------------------------------------------------------------------------
# Path setup — allows `pytest backend/tests/` to be run from the repo root
# without installing the backend package.
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_BACKEND_DIR))

import pytest
from fastapi.testclient import TestClient

from app.main import app

# A single shared client for the whole session.  TestClient manages the ASGI
# lifespan so startup/shutdown events are handled correctly.
client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _assert_no_server_error(response) -> None:
    """Fail fast with a readable message when the server returns 5xx."""
    assert response.status_code < 500, (
        f"Server error {response.status_code}: {response.text[:500]}"
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self):
        """GET /api/health must return HTTP 200 and status 'ok'."""
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body == {"status": "ok"}


# ---------------------------------------------------------------------------
# Territory — comunas list
# ---------------------------------------------------------------------------

class TestTerritoryComunas:
    def test_comunas_returns_200(self):
        """GET /api/territory/comunas must return HTTP 200."""
        response = client.get("/api/territory/comunas")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_comunas_returns_non_empty_list(self):
        """The comunas list must contain at least one entry."""
        response = client.get("/api/territory/comunas")
        assert response.status_code == 200
        body = response.json()
        assert "comunas" in body, "Response body must have a 'comunas' key"
        assert isinstance(body["comunas"], list), "'comunas' must be a list"
        assert len(body["comunas"]) > 0, "comunas list must not be empty"

    def test_each_comuna_has_required_fields(self):
        """Every entry in the comunas list must have a non-empty 'code' field."""
        response = client.get("/api/territory/comunas")
        assert response.status_code == 200
        comunas = response.json()["comunas"]
        for item in comunas:
            assert "code" in item, f"Missing 'code' in entry: {item}"
            assert isinstance(item["code"], str) and item["code"], (
                f"'code' must be a non-empty string, got: {item['code']!r}"
            )


# ---------------------------------------------------------------------------
# Dashboard overview — happy path
# ---------------------------------------------------------------------------

class TestDashboardOverviewAll:
    def test_overview_all_returns_200(self):
        """GET /api/dashboard/overview?comuna_code=ALL must return HTTP 200."""
        response = client.get("/api/dashboard/overview", params={"comuna_code": "ALL"})
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_overview_all_has_required_top_level_keys(self):
        """Response for ALL must contain 'metrics', 'recommendations', and 'city_averages'."""
        response = client.get("/api/dashboard/overview", params={"comuna_code": "ALL"})
        assert response.status_code == 200
        body = response.json()

        for key in ("metrics", "recommendations", "city_averages"):
            assert key in body, f"Missing required top-level key: '{key}'"

    def test_overview_all_metrics_structure(self):
        """Each metric in 'metrics' must be a dict with 'value' and 'unit' keys."""
        response = client.get("/api/dashboard/overview", params={"comuna_code": "ALL"})
        assert response.status_code == 200
        metrics = response.json()["metrics"]

        assert isinstance(metrics, dict), "'metrics' must be a dict"
        assert len(metrics) > 0, "'metrics' must not be empty"

        for metric_name, block in metrics.items():
            assert "value" in block, f"Metric '{metric_name}' missing 'value'"
            assert "unit" in block, f"Metric '{metric_name}' missing 'unit'"

    def test_overview_all_recommendations_is_list(self):
        """'recommendations' must be a non-empty list of strings."""
        response = client.get("/api/dashboard/overview", params={"comuna_code": "ALL"})
        assert response.status_code == 200
        recs = response.json()["recommendations"]

        assert isinstance(recs, list), "'recommendations' must be a list"
        assert len(recs) > 0, "'recommendations' must not be empty"
        for rec in recs:
            assert isinstance(rec, str), f"Each recommendation must be a string, got: {rec!r}"

    def test_overview_all_city_averages_structure(self):
        """'city_averages' must mirror the shape of 'metrics'."""
        response = client.get("/api/dashboard/overview", params={"comuna_code": "ALL"})
        assert response.status_code == 200
        body = response.json()
        city_avgs = body["city_averages"]

        assert isinstance(city_avgs, dict), "'city_averages' must be a dict"
        for key in ("mobility_equiv_vehicles", "safety_homicides", "investment_amount"):
            assert key in city_avgs, f"Expected city_average key '{key}' not found"
            block = city_avgs[key]
            assert "value" in block and "unit" in block, (
                f"city_averages['{key}'] must have 'value' and 'unit', got: {block}"
            )

    def test_overview_default_is_all(self):
        """Calling the endpoint without query params must behave identically to ALL."""
        response_default = client.get("/api/dashboard/overview")
        response_all = client.get("/api/dashboard/overview", params={"comuna_code": "ALL"})
        assert response_default.status_code == 200
        assert response_all.status_code == 200
        # Both must have the same top-level keys.
        assert set(response_default.json().keys()) == set(response_all.json().keys())


# ---------------------------------------------------------------------------
# Dashboard overview — invalid commune code returns 404
# ---------------------------------------------------------------------------

class TestDashboardOverviewInvalidCode:
    def test_invalid_comuna_code_returns_404(self):
        """GET /api/dashboard/overview?comuna_code=INVALID must return HTTP 404."""
        response = client.get("/api/dashboard/overview", params={"comuna_code": "INVALID"})
        assert response.status_code == 404, (
            f"Expected 404 for unknown comuna code, got {response.status_code}: {response.text}"
        )

    def test_invalid_comuna_code_error_body(self):
        """404 response for an unknown code must include a structured error detail."""
        response = client.get("/api/dashboard/overview", params={"comuna_code": "INVALID"})
        assert response.status_code == 404
        body = response.json()
        assert "detail" in body, "404 response must have a 'detail' field"
        detail = body["detail"]
        # The API wraps the detail as a dict with 'code' and 'message'.
        assert isinstance(detail, dict), f"'detail' must be a dict, got: {detail!r}"
        assert "code" in detail, "detail dict must have a 'code' key"
        assert "message" in detail, "detail dict must have a 'message' key"
        assert detail["code"] == "NOT_FOUND"

    def test_empty_string_comuna_code_is_rejected(self):
        """A blank commune code should return 422 (validation error), not 500."""
        # FastAPI enforces min_length=1 on the query param.
        response = client.get("/api/dashboard/overview", params={"comuna_code": ""})
        assert response.status_code == 422, (
            f"Expected 422 for empty commune code, got {response.status_code}"
        )
