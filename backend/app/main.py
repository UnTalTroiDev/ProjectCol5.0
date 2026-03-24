from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware

from .schemas.dashboard import (
    ComunasResponse, CrimeStatsResponse, OverviewResponse, TrendsResponse,
)
from .schemas.city import CitySummaryResponse
from .schemas.whatsapp import (
    AddSubscriberRequest, ManualSendResponse, NewsletterStatusResponse,
)
from .services.dashboard_service import (
    get_crime_stats, get_dashboard_compare, get_dashboard_overview,
    get_dashboard_trends, get_territory_comunas,
)
from .services.security_service import get_criminalidad_consolidada, get_violencia_intrafamiliar
from .services.health_service import get_natalidad, get_hospitalizacion
from .services.education_service import get_establecimientos, get_ambiente_escolar
from .services.environment_service import get_residuos_solidos
from .services.quality_service import get_imcv, get_siniestros_viales
from .services.newsletter_service import (
    add_subscriber, remove_subscriber, get_active_subscribers,
    get_newsletter_status, run_newsletter,
    start_scheduler, stop_scheduler, get_scheduler,
)
from .utils.normalize import normalize_code

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


def _check_admin(authorization: Optional[str]) -> None:
    """Validate the bearer token for admin endpoints."""
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail={
            "code": "ADMIN_NOT_CONFIGURED",
            "message": "ADMIN_TOKEN env var not set.",
        })
    if authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(status_code=401, detail={
            "code": "UNAUTHORIZED",
            "message": "Invalid or missing admin token.",
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop the newsletter scheduler with the app."""
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="MedCity Dashboard API",
    description=(
        "API para un dashboard de Medellin usando datos abiertos (MEData). "
        "Cubre movilidad, seguridad, salud, educacion, medio ambiente, calidad de vida y mas."
    ),
    version="0.5.0",
    lifespan=lifespan,
)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Sistema ────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["sistema"])
def health() -> dict:
    return {"status": "ok", "version": "0.5.0"}


# ── Territorio ─────────────────────────────────────────────────────────────

@app.get("/api/territory/comunas", response_model=ComunasResponse, tags=["territorio"])
def comunas() -> ComunasResponse:
    result = get_territory_comunas()
    return ComunasResponse(comunas=result)


# ── Dashboard principal ────────────────────────────────────────────────────

@app.get("/api/dashboard/overview", response_model=OverviewResponse, tags=["dashboard"])
def overview(
    comuna_code: str = Query("ALL", min_length=1, max_length=10,
                             description="Codigo de comuna o 'ALL'."),
    year: Optional[int] = Query(None, ge=2000, le=2100,
                                description="Año a consultar. Omitir = ultimo disponible."),
) -> OverviewResponse:
    comuna_code = comuna_code.strip()
    if comuna_code != "ALL":
        known = {c["code"] for c in get_territory_comunas()}
        norm = normalize_code(comuna_code)
        if norm not in known:
            raise HTTPException(status_code=404, detail={
                "code": "NOT_FOUND",
                "message": f"No existe la comuna '{comuna_code}'. Use /api/territory/comunas.",
            })
    return get_dashboard_overview(comuna_code=comuna_code, year=year)


@app.get("/api/dashboard/trends", response_model=TrendsResponse, tags=["dashboard"])
def trends(
    metric: str = Query(..., description="'mobility', 'safety' o 'investment'."),
    comuna_code: Optional[str] = Query(None, max_length=10),
) -> TrendsResponse:
    if metric not in {"mobility", "safety", "investment"}:
        raise HTTPException(status_code=422, detail={
            "code": "INVALID_METRIC",
            "message": f"Metrica '{metric}' no valida. Valores: mobility, safety, investment.",
        })
    return TrendsResponse(**get_dashboard_trends(metric=metric, comuna_code=comuna_code))


@app.get("/api/dashboard/compare", tags=["dashboard"])
def compare(
    comunas: str = Query(
        ...,
        description="Codigos de comuna separados por coma, ej: '01,04,09'.",
        min_length=1,
        max_length=100,
    ),
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> Dict[str, Any]:
    """
    Compara movilidad, homicidios e inversion publica para varias comunas.
    Pasa los codigos separados por coma: `?comunas=01,04,09`.
    """
    codes = [c.strip() for c in comunas.split(",") if c.strip()]
    if not codes:
        raise HTTPException(status_code=422, detail={"code": "NO_COMUNAS", "message": "Debes pasar al menos un codigo de comuna."})
    return get_dashboard_compare(comunas=codes, year=year)


@app.get("/api/dashboard/crime-stats", response_model=CrimeStatsResponse, tags=["dashboard"])
def crime_stats(
    comuna_code: Optional[str] = Query(None, max_length=10),
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> CrimeStatsResponse:
    return CrimeStatsResponse(**get_crime_stats(comuna_code=comuna_code, year=year))


# ── Seguridad ampliada ─────────────────────────────────────────────────────

@app.get("/api/security/criminalidad", tags=["seguridad"])
def criminalidad(
    year: Optional[int] = Query(None, ge=2000, le=2100,
                                description="Año a consultar. Omitir = todos los años."),
    crime_type: Optional[str] = Query(None, max_length=80,
                                      description="Filtrar por tipo de delito (ej: 'HOMICIDIO')."),
) -> Dict[str, Any]:
    """
    Criminalidad consolidada de Medellin: homicidios, hurtos (personas/carros/motos/residencias),
    extorsion, lesiones, violencia intrafamiliar, delitos sexuales.
    Fuente: SISC · MEData `1-027-23-000306`.
    """
    return get_criminalidad_consolidada(year=year, crime_type=crime_type)


@app.get("/api/security/violencia-intrafamiliar", tags=["seguridad"])
def violencia_intrafamiliar(
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> Dict[str, Any]:
    """
    Solicitudes de medidas de proteccion por violencia intrafamiliar por comuna y año.
    Fuente: Comisarias de Familia · MEData `1-027-23-000028`.
    """
    return get_violencia_intrafamiliar(year=year)


# ── Salud ──────────────────────────────────────────────────────────────────

@app.get("/api/health-data/natalidad", tags=["salud"])
def natalidad(
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> Dict[str, Any]:
    """
    Nacimientos en Medellin por año, sexo y comuna.
    Fuente: Secretaria de Salud · MEData `1-026-22-000029`.
    """
    return get_natalidad(year=year)


@app.get("/api/health-data/hospitalizacion", tags=["salud"])
def hospitalizacion(
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> Dict[str, Any]:
    """
    Egresos hospitalarios por diagnostico y año.
    Fuente: Secretaria de Salud · MEData `1-026-22-000126`.
    """
    return get_hospitalizacion(year=year)


# ── Educacion ──────────────────────────────────────────────────────────────

@app.get("/api/education/establecimientos", tags=["educacion"])
def establecimientos(
    comuna_code: Optional[str] = Query(None, max_length=10,
                                       description="Filtrar por codigo de comuna."),
) -> Dict[str, Any]:
    """
    Directorio de establecimientos educativos de Medellin por comuna y modalidad.
    Fuente: Secretaria de Educacion · MEData `1-011-08-000122`.
    """
    return get_establecimientos(comuna_code=comuna_code)


@app.get("/api/education/ambiente-escolar", tags=["educacion"])
def ambiente_escolar(
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> Dict[str, Any]:
    """
    Indicadores historicos de ambiente escolar (relaciones, comunicacion, participacion).
    Fuente: Secretaria de Educacion · MEData `1-011-08-000068`.
    """
    return get_ambiente_escolar(year=year)


# ── Medio Ambiente ─────────────────────────────────────────────────────────

@app.get("/api/environment/residuos", tags=["ambiente"])
def residuos(
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> Dict[str, Any]:
    """
    Generacion de residuos solidos (ordinarios y aprovechables) del Centro Administrativo
    Distrital por mes y tipo. Fuente: Secretaria de Suministros · MEData `1-028-02-000599`.
    """
    return get_residuos_solidos(year=year)


# ── Calidad de Vida ────────────────────────────────────────────────────────

@app.get("/api/quality/imcv", tags=["calidad-vida"])
def imcv(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    comuna_code: Optional[str] = Query(None, max_length=10),
) -> Dict[str, Any]:
    """
    Indice Multidimensional de Calidad de Vida (IMCV) por comuna y dimension
    (educacion, salud, seguridad social, vivienda, etc.).
    Fuente: DAP · MEData `1-002-09-000041`.
    """
    return get_imcv(year=year, comuna_code=comuna_code)


@app.get("/api/quality/siniestros-viales", tags=["calidad-vida"])
def siniestros_viales(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    comuna_code: Optional[str] = Query(None, max_length=10),
) -> Dict[str, Any]:
    """
    Victimas en incidentes viales por tipo, gravedad, comuna y año.
    Fuente: Secretaria de Movilidad · MEData `1-023-25-000360`.
    """
    return get_siniestros_viales(year=year, comuna_code=comuna_code)


# ── Resumen ciudad ─────────────────────────────────────────────────────────

@app.get("/api/city/summary", tags=["ciudad"])
def city_summary() -> Dict[str, Any]:
    """
    KPIs de alto nivel para todos los dominios de la ciudad.
    Agrega una llamada ligera a cada dominio y devuelve disponibilidad + metrica principal.
    """
    logger.info("GET /api/city/summary")

    domains: Dict[str, Any] = {}

    # Seguridad
    try:
        crim = get_criminalidad_consolidada()
        domains["seguridad"] = {
            "available": crim.get("available", False),
            "label": "Criminalidad consolidada",
            "latest_year": crim.get("available_years", [None])[-1] if crim.get("available_years") else None,
            "total_tipos": len(crim.get("by_type", [])),
            "dataset_url": crim.get("dataset_url"),
        }
    except Exception as e:
        domains["seguridad"] = {"available": False, "reason": str(e)}

    # Salud — natalidad
    try:
        nat = get_natalidad()
        domains["salud"] = {
            "available": nat.get("available", False),
            "label": "Natalidad",
            "latest_year": nat.get("latest_year"),
            "total_nacimientos": nat.get("total_nacimientos"),
            "dataset_url": nat.get("dataset_url"),
        }
    except Exception as e:
        domains["salud"] = {"available": False, "reason": str(e)}

    # Educacion
    try:
        edu = get_establecimientos()
        domains["educacion"] = {
            "available": edu.get("available", False),
            "label": "Establecimientos educativos",
            "total_establecimientos": edu.get("total"),
            "dataset_url": edu.get("dataset_url"),
        }
    except Exception as e:
        domains["educacion"] = {"available": False, "reason": str(e)}

    # Medio Ambiente
    try:
        env = get_residuos_solidos()
        domains["ambiente"] = {
            "available": env.get("available", False),
            "label": "Residuos solidos",
            "latest_year": env.get("latest_year"),
            "total_kg": env.get("total_kg"),
            "dataset_url": env.get("dataset_url"),
        }
    except Exception as e:
        domains["ambiente"] = {"available": False, "reason": str(e)}

    # Calidad de vida
    try:
        imcv_data = get_imcv()
        domains["calidad_vida"] = {
            "available": imcv_data.get("available", False),
            "label": "IMCV — Calidad de Vida",
            "latest_year": imcv_data.get("latest_year"),
            "total_comunas": len(imcv_data.get("by_comuna", [])),
            "dataset_url": imcv_data.get("dataset_url"),
        }
    except Exception as e:
        domains["calidad_vida"] = {"available": False, "reason": str(e)}

    # Siniestros viales
    try:
        sin = get_siniestros_viales()
        domains["siniestros_viales"] = {
            "available": sin.get("available", False),
            "label": "Victimas incidentes viales",
            "latest_year": sin.get("latest_year"),
            "total_victimas": sin.get("total_victimas"),
            "dataset_url": sin.get("dataset_url"),
        }
    except Exception as e:
        domains["siniestros_viales"] = {"available": False, "reason": str(e)}

    # Violencia intrafamiliar
    try:
        vif = get_violencia_intrafamiliar()
        domains["violencia_intrafamiliar"] = {
            "available": vif.get("available", False),
            "label": "Violencia intrafamiliar",
            "latest_year": vif.get("latest_year"),
            "total": vif.get("total"),
            "dataset_url": vif.get("dataset_url"),
        }
    except Exception as e:
        domains["violencia_intrafamiliar"] = {"available": False, "reason": str(e)}

    available_count = sum(1 for d in domains.values() if d.get("available"))
    return {
        "domains": domains,
        "available_domains": available_count,
        "total_domains": len(domains),
        "message": f"{available_count}/{len(domains)} dominios de datos disponibles en MEData.",
    }


# ── Newsletter WhatsApp ──────────────────────────────────────────────────

@app.get("/api/newsletter/status", response_model=NewsletterStatusResponse, tags=["newsletter"])
def newsletter_status() -> NewsletterStatusResponse:
    """Estado de la integracion de newsletter WhatsApp."""
    data = get_newsletter_status(scheduler=get_scheduler())
    return NewsletterStatusResponse(**data)


@app.get("/api/newsletter/subscribers", tags=["newsletter"])
def newsletter_list_subscribers(
    authorization: Optional[str] = Header(None),
) -> List[Dict[str, Any]]:
    """Lista de suscriptores activos (requiere ADMIN_TOKEN)."""
    _check_admin(authorization)
    return get_active_subscribers()


@app.post("/api/newsletter/subscribers", tags=["newsletter"])
def newsletter_add_subscriber(
    req: AddSubscriberRequest,
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Agrega un numero de telefono al newsletter diario (requiere ADMIN_TOKEN)."""
    _check_admin(authorization)
    return add_subscriber(phone_number=req.phone_number, comuna_code=req.comuna_code)


@app.delete("/api/newsletter/subscribers", tags=["newsletter"])
def newsletter_remove_subscriber(
    phone_number: str = Query(..., min_length=10, max_length=16,
                              description="Numero en formato E.164 (ej: +573001234567)."),
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Elimina un numero del newsletter (requiere ADMIN_TOKEN)."""
    _check_admin(authorization)
    return remove_subscriber(phone_number=phone_number)


@app.post("/api/newsletter/send-now", response_model=ManualSendResponse, tags=["newsletter"])
def newsletter_send_now(
    authorization: Optional[str] = Header(None),
) -> ManualSendResponse:
    """Envia el newsletter inmediatamente a todos los suscriptores activos (requiere ADMIN_TOKEN)."""
    _check_admin(authorization)
    result = run_newsletter()
    return ManualSendResponse(**result)
