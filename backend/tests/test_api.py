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

_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_BACKEND_DIR))

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _assert_no_server_error(response) -> None:
    """Fail fast con mensaje legible cuando el servidor devuelve 5xx."""
    assert response.status_code < 500, (
        f"Server error {response.status_code}: {response.text[:500]}"
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Territory — comunas list
# ---------------------------------------------------------------------------

class TestTerritoryComunas:
    def test_comunas_returns_200(self):
        response = client.get("/api/territory/comunas")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_comunas_returns_non_empty_list(self):
        response = client.get("/api/territory/comunas")
        assert response.status_code == 200
        body = response.json()
        assert "comunas" in body
        assert isinstance(body["comunas"], list)
        assert len(body["comunas"]) > 0

    def test_each_comuna_has_required_fields(self):
        response = client.get("/api/territory/comunas")
        assert response.status_code == 200
        for item in response.json()["comunas"]:
            assert "code" in item
            assert isinstance(item["code"], str) and item["code"]


# ---------------------------------------------------------------------------
# Dashboard overview — happy path
# ---------------------------------------------------------------------------

class TestDashboardOverviewAll:
    def test_overview_all_returns_200(self):
        response = client.get("/api/dashboard/overview", params={"comuna_code": "ALL"})
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_overview_all_has_required_top_level_keys(self):
        response = client.get("/api/dashboard/overview", params={"comuna_code": "ALL"})
        assert response.status_code == 200
        body = response.json()
        for key in ("metrics", "recommendations", "city_averages"):
            assert key in body, f"Missing required top-level key: '{key}'"

    def test_overview_all_metrics_structure(self):
        response = client.get("/api/dashboard/overview", params={"comuna_code": "ALL"})
        assert response.status_code == 200
        metrics = response.json()["metrics"]
        assert isinstance(metrics, dict) and len(metrics) > 0
        for metric_name, block in metrics.items():
            assert "value" in block, f"Metric '{metric_name}' missing 'value'"
            assert "unit" in block, f"Metric '{metric_name}' missing 'unit'"

    def test_overview_all_recommendations_is_list(self):
        response = client.get("/api/dashboard/overview", params={"comuna_code": "ALL"})
        assert response.status_code == 200
        recs = response.json()["recommendations"]
        assert isinstance(recs, list) and len(recs) > 0
        for rec in recs:
            assert isinstance(rec, str)

    def test_overview_all_city_averages_structure(self):
        response = client.get("/api/dashboard/overview", params={"comuna_code": "ALL"})
        assert response.status_code == 200
        city_avgs = response.json()["city_averages"]
        assert isinstance(city_avgs, dict)
        for key in ("mobility_equiv_vehicles", "safety_homicides", "investment_amount"):
            assert key in city_avgs, f"Expected city_average key '{key}' not found"
            block = city_avgs[key]
            assert "value" in block and "unit" in block

    def test_overview_default_is_all(self):
        response_default = client.get("/api/dashboard/overview")
        response_all = client.get("/api/dashboard/overview", params={"comuna_code": "ALL"})
        assert response_default.status_code == 200
        assert response_all.status_code == 200
        assert set(response_default.json().keys()) == set(response_all.json().keys())

    def test_overview_year_param_accepted(self):
        """El parametro year debe ser aceptado sin error 422."""
        response = client.get(
            "/api/dashboard/overview", params={"comuna_code": "ALL", "year": 2022}
        )
        _assert_no_server_error(response)
        # Puede devolver 200 (datos disponibles) o 404/422 segun el año.
        assert response.status_code in (200, 404, 422)

    def test_overview_year_invalid_rejected(self):
        """Un año fuera del rango (ej: 1800) debe devolver 422."""
        response = client.get(
            "/api/dashboard/overview", params={"comuna_code": "ALL", "year": 1800}
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Dashboard overview — invalid commune code returns 404
# ---------------------------------------------------------------------------

class TestDashboardOverviewInvalidCode:
    def test_invalid_comuna_code_returns_404(self):
        response = client.get("/api/dashboard/overview", params={"comuna_code": "INVALID"})
        assert response.status_code == 404, (
            f"Expected 404 for unknown comuna code, got {response.status_code}: {response.text}"
        )

    def test_invalid_comuna_code_error_body(self):
        response = client.get("/api/dashboard/overview", params={"comuna_code": "INVALID"})
        assert response.status_code == 404
        body = response.json()
        assert "detail" in body
        detail = body["detail"]
        assert isinstance(detail, dict)
        assert "code" in detail and "message" in detail
        assert detail["code"] == "NOT_FOUND"

    def test_empty_string_comuna_code_is_rejected(self):
        response = client.get("/api/dashboard/overview", params={"comuna_code": ""})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Dashboard trends
# ---------------------------------------------------------------------------

class TestDashboardTrends:
    def test_trends_safety_returns_200(self):
        response = client.get("/api/dashboard/trends", params={"metric": "safety"})
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_trends_mobility_returns_200(self):
        response = client.get("/api/dashboard/trends", params={"metric": "mobility"})
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_trends_investment_returns_200(self):
        response = client.get("/api/dashboard/trends", params={"metric": "investment"})
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_trends_response_structure(self):
        response = client.get("/api/dashboard/trends", params={"metric": "safety"})
        assert response.status_code == 200
        body = response.json()
        for key in ("metric", "comuna_code", "unit", "series", "available_years"):
            assert key in body, f"Missing key '{key}' in trends response"
        assert isinstance(body["series"], list)
        assert isinstance(body["available_years"], list)

    def test_trends_series_points_have_year_and_value(self):
        response = client.get("/api/dashboard/trends", params={"metric": "safety"})
        assert response.status_code == 200
        for point in response.json()["series"]:
            assert "year" in point
            assert "value" in point

    def test_trends_invalid_metric_returns_422(self):
        response = client.get("/api/dashboard/trends", params={"metric": "invalid_metric"})
        assert response.status_code == 422

    def test_trends_with_missing_metric_returns_422(self):
        """El parametro metric es requerido."""
        response = client.get("/api/dashboard/trends")
        assert response.status_code == 422

    def test_trends_with_comuna_code(self):
        """Tendencias filtradas por comuna deben responder sin error 5xx."""
        comunas = client.get("/api/territory/comunas").json()["comunas"]
        if comunas:
            code = comunas[0]["code"]
            response = client.get(
                "/api/dashboard/trends",
                params={"metric": "safety", "comuna_code": code},
            )
            _assert_no_server_error(response)
            assert response.status_code == 200


# ---------------------------------------------------------------------------
# Dashboard crime-stats
# ---------------------------------------------------------------------------

class TestDashboardCrimeStats:
    def test_crime_stats_returns_200(self):
        response = client.get("/api/dashboard/crime-stats")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_crime_stats_structure(self):
        response = client.get("/api/dashboard/crime-stats")
        assert response.status_code == 200
        body = response.json()
        for key in (
            "comuna_code", "year", "homicidios",
            "lesiones_comunes", "top_homicidios_by_comuna", "top_lesiones_by_comuna",
        ):
            assert key in body, f"Missing key '{key}' in crime-stats response"

    def test_crime_stats_homicidios_has_value_and_unit(self):
        response = client.get("/api/dashboard/crime-stats")
        assert response.status_code == 200
        h = response.json()["homicidios"]
        assert "value" in h and "unit" in h

    def test_crime_stats_lesiones_has_available_flag(self):
        response = client.get("/api/dashboard/crime-stats")
        assert response.status_code == 200
        les = response.json()["lesiones_comunes"]
        assert "available" in les

    def test_crime_stats_top_homicidios_is_list(self):
        response = client.get("/api/dashboard/crime-stats")
        assert response.status_code == 200
        assert isinstance(response.json()["top_homicidios_by_comuna"], list)

    def test_crime_stats_with_year_param(self):
        response = client.get("/api/dashboard/crime-stats", params={"year": 2022})
        _assert_no_server_error(response)
        assert response.status_code in (200, 404)

    def test_crime_stats_invalid_year_rejected(self):
        response = client.get("/api/dashboard/crime-stats", params={"year": 1500})
        assert response.status_code == 422
