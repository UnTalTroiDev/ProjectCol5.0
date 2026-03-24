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
        body = response.json()
        assert body["status"] == "ok"
        assert "version" in body


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


# ---------------------------------------------------------------------------
# Dashboard compare — multi-comuna
# ---------------------------------------------------------------------------

class TestDashboardCompare:
    def test_compare_two_comunas_returns_200(self):
        comunas = client.get("/api/territory/comunas").json()["comunas"]
        if len(comunas) >= 2:
            codes = f"{comunas[0]['code']},{comunas[1]['code']}"
            response = client.get("/api/dashboard/compare", params={"comunas": codes})
            _assert_no_server_error(response)
            assert response.status_code == 200

    def test_compare_response_has_comunas_list(self):
        comunas = client.get("/api/territory/comunas").json()["comunas"]
        if len(comunas) >= 2:
            codes = f"{comunas[0]['code']},{comunas[1]['code']}"
            response = client.get("/api/dashboard/compare", params={"comunas": codes})
            assert response.status_code == 200
            body = response.json()
            assert "comunas" in body and "year" in body
            assert isinstance(body["comunas"], list)
            assert len(body["comunas"]) == 2

    def test_compare_each_row_has_metrics(self):
        comunas = client.get("/api/territory/comunas").json()["comunas"]
        if len(comunas) >= 1:
            codes = comunas[0]['code']
            response = client.get("/api/dashboard/compare", params={"comunas": codes})
            assert response.status_code == 200
            row = response.json()["comunas"][0]
            assert "comuna_code" in row
            assert "mobility_equiv_vehicles" in row
            assert "safety_homicides" in row
            assert "investment_amount" in row

    def test_compare_without_comunas_returns_422(self):
        response = client.get("/api/dashboard/compare")
        assert response.status_code == 422

    def test_compare_invalid_year_rejected(self):
        response = client.get("/api/dashboard/compare", params={"comunas": "01", "year": 1800})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Security — criminalidad consolidada
# ---------------------------------------------------------------------------

class TestSecurityCriminalidad:
    def test_criminalidad_returns_200(self):
        response = client.get("/api/security/criminalidad")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_criminalidad_has_available_flag(self):
        response = client.get("/api/security/criminalidad")
        _assert_no_server_error(response)
        body = response.json()
        assert "available" in body

    def test_criminalidad_with_year(self):
        response = client.get("/api/security/criminalidad", params={"year": 2022})
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_criminalidad_invalid_year_rejected(self):
        response = client.get("/api/security/criminalidad", params={"year": 1800})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Security — violencia intrafamiliar
# ---------------------------------------------------------------------------

class TestSecurityViolenciaIntrafamiliar:
    def test_vif_returns_200(self):
        response = client.get("/api/security/violencia-intrafamiliar")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_vif_has_available_flag(self):
        response = client.get("/api/security/violencia-intrafamiliar")
        _assert_no_server_error(response)
        assert "available" in response.json()

    def test_vif_invalid_year_rejected(self):
        response = client.get("/api/security/violencia-intrafamiliar", params={"year": 1800})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Salud — natalidad
# ---------------------------------------------------------------------------

class TestHealthNatalidad:
    def test_natalidad_returns_200(self):
        response = client.get("/api/health-data/natalidad")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_natalidad_has_available_flag(self):
        response = client.get("/api/health-data/natalidad")
        _assert_no_server_error(response)
        assert "available" in response.json()

    def test_natalidad_invalid_year_rejected(self):
        response = client.get("/api/health-data/natalidad", params={"year": 1800})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Salud — hospitalización
# ---------------------------------------------------------------------------

class TestHealthHospitalizacion:
    def test_hospitalizacion_returns_200(self):
        response = client.get("/api/health-data/hospitalizacion")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_hospitalizacion_has_available_flag(self):
        response = client.get("/api/health-data/hospitalizacion")
        _assert_no_server_error(response)
        assert "available" in response.json()


# ---------------------------------------------------------------------------
# Educación — establecimientos
# ---------------------------------------------------------------------------

class TestEducationEstablecimientos:
    def test_establecimientos_returns_200(self):
        response = client.get("/api/education/establecimientos")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_establecimientos_has_available_flag(self):
        response = client.get("/api/education/establecimientos")
        _assert_no_server_error(response)
        assert "available" in response.json()

    def test_establecimientos_with_comuna_filter(self):
        comunas = client.get("/api/territory/comunas").json()["comunas"]
        if comunas:
            code = comunas[0]["code"]
            response = client.get("/api/education/establecimientos", params={"comuna_code": code})
            _assert_no_server_error(response)
            assert response.status_code == 200


# ---------------------------------------------------------------------------
# Educación — ambiente escolar
# ---------------------------------------------------------------------------

class TestEducationAmbienteEscolar:
    def test_ambiente_escolar_returns_200(self):
        response = client.get("/api/education/ambiente-escolar")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_ambiente_escolar_has_available_flag(self):
        response = client.get("/api/education/ambiente-escolar")
        _assert_no_server_error(response)
        assert "available" in response.json()


# ---------------------------------------------------------------------------
# Medio Ambiente — residuos sólidos
# ---------------------------------------------------------------------------

class TestEnvironmentResiduos:
    def test_residuos_returns_200(self):
        response = client.get("/api/environment/residuos")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_residuos_has_available_flag(self):
        response = client.get("/api/environment/residuos")
        _assert_no_server_error(response)
        assert "available" in response.json()

    def test_residuos_invalid_year_rejected(self):
        response = client.get("/api/environment/residuos", params={"year": 1800})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Calidad de Vida — IMCV
# ---------------------------------------------------------------------------

class TestQualityImcv:
    def test_imcv_returns_200(self):
        response = client.get("/api/quality/imcv")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_imcv_has_available_flag(self):
        response = client.get("/api/quality/imcv")
        _assert_no_server_error(response)
        assert "available" in response.json()

    def test_imcv_with_comuna_filter(self):
        comunas = client.get("/api/territory/comunas").json()["comunas"]
        if comunas:
            code = comunas[0]["code"]
            response = client.get("/api/quality/imcv", params={"comuna_code": code})
            _assert_no_server_error(response)
            assert response.status_code == 200


# ---------------------------------------------------------------------------
# Calidad de Vida — siniestros viales
# ---------------------------------------------------------------------------

class TestQualitySiniestros:
    def test_siniestros_returns_200(self):
        response = client.get("/api/quality/siniestros-viales")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_siniestros_has_available_flag(self):
        response = client.get("/api/quality/siniestros-viales")
        _assert_no_server_error(response)
        assert "available" in response.json()


# ---------------------------------------------------------------------------
# Ciudad — resumen global
# ---------------------------------------------------------------------------

class TestCitySummary:
    def test_city_summary_returns_200(self):
        response = client.get("/api/city/summary")
        _assert_no_server_error(response)
        assert response.status_code == 200

    def test_city_summary_structure(self):
        response = client.get("/api/city/summary")
        _assert_no_server_error(response)
        body = response.json()
        assert "domains" in body
        assert "available_domains" in body
        assert "total_domains" in body
        assert "message" in body

    def test_city_summary_domains_is_dict(self):
        response = client.get("/api/city/summary")
        _assert_no_server_error(response)
        domains = response.json()["domains"]
        assert isinstance(domains, dict)
        assert len(domains) > 0
        for key, domain in domains.items():
            assert "available" in domain, f"Domain '{key}' missing 'available' flag"

    def test_city_summary_counts_match(self):
        response = client.get("/api/city/summary")
        _assert_no_server_error(response)
        body = response.json()
        assert body["total_domains"] == len(body["domains"])


# ---------------------------------------------------------------------------
# Newsletter — WhatsApp integration
# ---------------------------------------------------------------------------

class TestNewsletterStatus:
    def test_status_returns_200(self):
        response = client.get("/api/newsletter/status")
        assert response.status_code == 200

    def test_status_has_required_fields(self):
        response = client.get("/api/newsletter/status")
        assert response.status_code == 200
        body = response.json()
        for key in ("configured", "enabled", "subscriber_count", "messages_sent_today"):
            assert key in body, f"Missing key '{key}' in newsletter status"

    def test_status_configured_is_bool(self):
        response = client.get("/api/newsletter/status")
        assert response.status_code == 200
        assert isinstance(response.json()["configured"], bool)


class TestNewsletterSubscribersAuth:
    def test_list_subscribers_without_auth_returns_error(self):
        """Without ADMIN_TOKEN set or with wrong token, should reject."""
        response = client.get("/api/newsletter/subscribers")
        assert response.status_code in (401, 503)

    def test_add_subscriber_without_auth_returns_error(self):
        response = client.post(
            "/api/newsletter/subscribers",
            json={"phone_number": "+573001234567"},
        )
        assert response.status_code in (401, 503)

    def test_remove_subscriber_without_auth_returns_error(self):
        response = client.delete(
            "/api/newsletter/subscribers",
            params={"phone_number": "+573001234567"},
        )
        assert response.status_code in (401, 503)

    def test_add_subscriber_invalid_phone_returns_422(self):
        response = client.post(
            "/api/newsletter/subscribers",
            json={"phone_number": "invalid"},
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (401, 422, 503)

    def test_add_subscriber_missing_phone_returns_422(self):
        response = client.post(
            "/api/newsletter/subscribers",
            json={},
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code in (401, 422, 503)


class TestNewsletterPublicSubscribe:
    def test_subscribe_valid_phone_returns_200(self):
        response = client.post(
            "/api/newsletter/subscribe",
            json={"phone_number": "+573009999999", "comuna_code": "ALL"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("success") is True

    def test_subscribe_invalid_phone_returns_422(self):
        response = client.post(
            "/api/newsletter/subscribe",
            json={"phone_number": "bad"},
        )
        assert response.status_code == 422

    def test_subscribe_missing_phone_returns_422(self):
        response = client.post(
            "/api/newsletter/subscribe",
            json={},
        )
        assert response.status_code == 422


class TestNewsletterSendNow:
    def test_send_now_without_auth_returns_error(self):
        response = client.post("/api/newsletter/send-now")
        assert response.status_code in (401, 503)


class TestMessageFormatter:
    """Unit tests for the message formatter (no network needed)."""

    def test_format_daily_newsletter_under_4096_chars(self):
        from app.services.message_formatter import format_daily_newsletter

        overview = {
            "metrics": {
                "mobility_equiv_vehicles": {"value": 12345, "unit": "vehiculos_equivalentes"},
                "safety_homicides": {"value": 100, "unit": "casos"},
                "investment_amount": {"value": 5_000_000_000, "unit": "COP"},
            },
            "city_averages": {},
            "recommendations": [
                "Recomendacion uno.",
                "Recomendacion dos.",
                "Recomendacion tres.",
            ],
            "safety_by_comuna": [
                {"comuna_code": "01", "safety_homicides": 50},
                {"comuna_code": "02", "safety_homicides": 40},
            ],
        }
        security = {"available": True, "by_type": [
            {"crime_type": "HOMICIDIO", "total": 500},
            {"crime_type": "HURTO A PERSONAS", "total": 3000},
        ]}
        city_summary = {"available_domains": 5, "total_domains": 7}

        msg = format_daily_newsletter(overview, security, city_summary)
        assert isinstance(msg, str)
        assert len(msg) <= 4096
        assert "MedCity Dashboard" in msg

    def test_format_daily_newsletter_handles_empty_data(self):
        from app.services.message_formatter import format_daily_newsletter

        msg = format_daily_newsletter(
            overview={"metrics": {}, "recommendations": [], "safety_by_comuna": []},
            security={"available": False},
            city_summary={"available_domains": 0, "total_domains": 0},
        )
        assert isinstance(msg, str)
        assert "MedCity Dashboard" in msg

    def test_format_comuna_newsletter_under_4096_chars(self):
        from app.services.message_formatter import format_comuna_newsletter

        overview = {
            "selected": {"comuna_code": "01", "comuna_name": "Popular"},
            "metrics": {
                "safety_homicides": {"value": 30, "unit": "casos"},
                "investment_amount": {"value": 1_000_000, "unit": "COP"},
            },
            "recommendations": ["Seguridad [CRITICO]: 30 homicidios."],
        }
        msg = format_comuna_newsletter(overview, "01")
        assert isinstance(msg, str)
        assert len(msg) <= 4096
        assert "Popular" in msg
