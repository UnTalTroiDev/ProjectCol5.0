from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .schemas.dashboard import (
    ComunasResponse, CrimeStatsResponse, OverviewResponse, TrendsResponse,
)
from .schemas.city import CitySummaryResponse
from .schemas.domains import (
    CriminalidadResponse as CriminalidadModel,
    ViolenciaIntrafamiliarResponse as VifModel,
    NatalidadResponse as NatalidadModel,
    HospitalizacionResponse as HospitalizacionModel,
    EstablecimientosResponse as EstablecimientosModel,
    AmbienteEscolarResponse as AmbienteEscolarModel,
    ResiduosResponse as ResiduosModel,
    ImcvResponse as ImcvModel,
    SiniestrosResponse as SiniestrosModel,
    CompareResponse as CompareModel,
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
from .utils.normalize import normalize_code

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="MedCity Dashboard API",
    description=(
        "API para un dashboard de Medellin usando datos abiertos (MEData). "
        "Cubre movilidad, seguridad, salud, educacion, medio ambiente, calidad de vida y mas."
    ),
    version="0.4.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Sistema ────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["sistema"])
def health() -> dict:
    return {"status": "ok", "version": "0.4.0"}


@app.get("/api/health/deep", tags=["sistema"])
async def health_deep() -> dict:
    """Deep health check: verifies connectivity to upstream MEData CSVs."""
    import httpx
    import time

    checks: Dict[str, Any] = {}
    t0 = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.head("https://medata.gov.co", follow_redirects=True)
            checks["medata_reachable"] = resp.status_code < 500
            checks["medata_status"] = resp.status_code
    except Exception:
        checks["medata_reachable"] = False

    elapsed = time.monotonic() - t0
    overall = all(v for k, v in checks.items() if k.endswith("_reachable"))
    return {
        "status": "ok" if overall else "degraded",
        "version": "0.4.0",
        "checks": checks,
        "elapsed_ms": round(elapsed * 1000),
    }


# ── Territorio ─────────────────────────────────────────────────────────────

@app.get("/api/territory/comunas", response_model=ComunasResponse, tags=["territorio"])
async def comunas() -> ComunasResponse:
    result = await get_territory_comunas()
    return ComunasResponse(comunas=result)


# ── Dashboard principal ────────────────────────────────────────────────────

@app.get("/api/dashboard/overview", response_model=OverviewResponse, tags=["dashboard"])
async def overview(
    comuna_code: str = Query("ALL", min_length=1, max_length=10,
                             description="Codigo de comuna o 'ALL'."),
    year: Optional[int] = Query(None, ge=2000, le=2100,
                                description="Año a consultar. Omitir = ultimo disponible."),
) -> OverviewResponse:
    comuna_code = comuna_code.strip()
    if comuna_code != "ALL":
        known = {c["code"] for c in await get_territory_comunas()}
        norm = normalize_code(comuna_code)
        if norm not in known:
            raise HTTPException(status_code=404, detail={
                "code": "NOT_FOUND",
                "message": f"No existe la comuna '{comuna_code}'. Use /api/territory/comunas.",
            })
    return await get_dashboard_overview(comuna_code=comuna_code, year=year)


@app.get("/api/dashboard/trends", response_model=TrendsResponse, tags=["dashboard"])
async def trends(
    metric: str = Query(..., description="'mobility', 'safety' o 'investment'."),
    comuna_code: Optional[str] = Query(None, max_length=10),
) -> TrendsResponse:
    if metric not in {"mobility", "safety", "investment"}:
        raise HTTPException(status_code=422, detail={
            "code": "INVALID_METRIC",
            "message": f"Metrica '{metric}' no valida. Valores: mobility, safety, investment.",
        })
    return TrendsResponse(**(await get_dashboard_trends(metric=metric, comuna_code=comuna_code)))


@app.get("/api/dashboard/compare", response_model=CompareModel, tags=["dashboard"])
async def compare(
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
    return await get_dashboard_compare(comunas=codes, year=year)


@app.get("/api/dashboard/crime-stats", response_model=CrimeStatsResponse, tags=["dashboard"])
async def crime_stats(
    comuna_code: Optional[str] = Query(None, max_length=10),
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> CrimeStatsResponse:
    return CrimeStatsResponse(**(await get_crime_stats(comuna_code=comuna_code, year=year)))


# ── Seguridad ampliada ─────────────────────────────────────────────────────

@app.get("/api/security/criminalidad", response_model=CriminalidadModel, tags=["seguridad"])
async def criminalidad(
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
    return await get_criminalidad_consolidada(year=year, crime_type=crime_type)


@app.get("/api/security/violencia-intrafamiliar", response_model=VifModel, tags=["seguridad"])
async def violencia_intrafamiliar(
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> Dict[str, Any]:
    """
    Solicitudes de medidas de proteccion por violencia intrafamiliar por comuna y año.
    Fuente: Comisarias de Familia · MEData `1-027-23-000028`.
    """
    return await get_violencia_intrafamiliar(year=year)


# ── Salud ──────────────────────────────────────────────────────────────────

@app.get("/api/health-data/natalidad", response_model=NatalidadModel, tags=["salud"])
async def natalidad(
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> Dict[str, Any]:
    """
    Nacimientos en Medellin por año, sexo y comuna.
    Fuente: Secretaria de Salud · MEData `1-026-22-000029`.
    """
    return await get_natalidad(year=year)


@app.get("/api/health-data/hospitalizacion", response_model=HospitalizacionModel, tags=["salud"])
async def hospitalizacion(
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> Dict[str, Any]:
    """
    Egresos hospitalarios por diagnostico y año.
    Fuente: Secretaria de Salud · MEData `1-026-22-000126`.
    """
    return await get_hospitalizacion(year=year)


# ── Educacion ──────────────────────────────────────────────────────────────

@app.get("/api/education/establecimientos", response_model=EstablecimientosModel, tags=["educacion"])
async def establecimientos(
    comuna_code: Optional[str] = Query(None, max_length=10,
                                       description="Filtrar por codigo de comuna."),
    page: int = Query(1, ge=1, description="Numero de pagina (1-indexed)."),
    page_size: int = Query(50, ge=1, le=200, description="Registros por pagina (max 200)."),
) -> Dict[str, Any]:
    """
    Directorio de establecimientos educativos de Medellin por comuna y modalidad.
    Fuente: Secretaria de Educacion · MEData `1-011-08-000122`.
    """
    return await get_establecimientos(comuna_code=comuna_code, page=page, page_size=page_size)


@app.get("/api/education/ambiente-escolar", response_model=AmbienteEscolarModel, tags=["educacion"])
async def ambiente_escolar(
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> Dict[str, Any]:
    """
    Indicadores historicos de ambiente escolar (relaciones, comunicacion, participacion).
    Fuente: Secretaria de Educacion · MEData `1-011-08-000068`.
    """
    return await get_ambiente_escolar(year=year)


# ── Medio Ambiente ─────────────────────────────────────────────────────────

@app.get("/api/environment/residuos", response_model=ResiduosModel, tags=["ambiente"])
async def residuos(
    year: Optional[int] = Query(None, ge=2000, le=2100),
) -> Dict[str, Any]:
    """
    Generacion de residuos solidos (ordinarios y aprovechables) del Centro Administrativo
    Distrital por mes y tipo. Fuente: Secretaria de Suministros · MEData `1-028-02-000599`.
    """
    return await get_residuos_solidos(year=year)


# ── Calidad de Vida ────────────────────────────────────────────────────────

@app.get("/api/quality/imcv", response_model=ImcvModel, tags=["calidad-vida"])
async def imcv(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    comuna_code: Optional[str] = Query(None, max_length=10),
) -> Dict[str, Any]:
    """
    Indice Multidimensional de Calidad de Vida (IMCV) por comuna y dimension
    (educacion, salud, seguridad social, vivienda, etc.).
    Fuente: DAP · MEData `1-002-09-000041`.
    """
    return await get_imcv(year=year, comuna_code=comuna_code)


@app.get("/api/quality/siniestros-viales", response_model=SiniestrosModel, tags=["calidad-vida"])
async def siniestros_viales(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    comuna_code: Optional[str] = Query(None, max_length=10),
) -> Dict[str, Any]:
    """
    Victimas en incidentes viales por tipo, gravedad, comuna y año.
    Fuente: Secretaria de Movilidad · MEData `1-023-25-000360`.
    """
    return await get_siniestros_viales(year=year, comuna_code=comuna_code)


# ── Resumen ciudad ─────────────────────────────────────────────────────────

@app.get("/api/city/summary", tags=["ciudad"])
@limiter.limit("10/minute")
async def city_summary(request: Request) -> Dict[str, Any]:
    """
    KPIs de alto nivel para todos los dominios de la ciudad.
    Agrega una llamada ligera a cada dominio y devuelve disponibilidad + metrica principal.
    """
    import asyncio
    logger.info("GET /api/city/summary")

    domains: Dict[str, Any] = {}

    # Fetch all domains in parallel (H1 fix)
    results = await asyncio.gather(
        get_criminalidad_consolidada(),
        get_natalidad(),
        get_establecimientos(),
        get_residuos_solidos(),
        get_imcv(),
        get_siniestros_viales(),
        get_violencia_intrafamiliar(),
        return_exceptions=True,
    )

    crim, nat, edu, env, imcv_data, sin, vif = results

    def _safe_reason(exc: Exception) -> str:
        """Return a sanitized error reason without internal paths or stack traces."""
        logger.warning("city/summary domain error: %s", exc)
        return "Fuente de datos temporalmente no disponible."

    # Seguridad
    if isinstance(crim, Exception):
        domains["seguridad"] = {"available": False, "reason": _safe_reason(crim)}
    else:
        domains["seguridad"] = {
            "available": crim.get("available", False),
            "label": "Criminalidad consolidada",
            "latest_year": crim.get("available_years", [None])[-1] if crim.get("available_years") else None,
            "total_tipos": len(crim.get("by_type", [])),
            "dataset_url": crim.get("dataset_url"),
        }

    # Salud — natalidad
    if isinstance(nat, Exception):
        domains["salud"] = {"available": False, "reason": _safe_reason(nat)}
    else:
        domains["salud"] = {
            "available": nat.get("available", False),
            "label": "Natalidad",
            "latest_year": nat.get("latest_year"),
            "total_nacimientos": nat.get("total_nacimientos"),
            "dataset_url": nat.get("dataset_url"),
        }

    # Educacion
    if isinstance(edu, Exception):
        domains["educacion"] = {"available": False, "reason": _safe_reason(edu)}
    else:
        domains["educacion"] = {
            "available": edu.get("available", False),
            "label": "Establecimientos educativos",
            "total_establecimientos": edu.get("total"),
            "dataset_url": edu.get("dataset_url"),
        }

    # Medio Ambiente
    if isinstance(env, Exception):
        domains["ambiente"] = {"available": False, "reason": _safe_reason(env)}
    else:
        domains["ambiente"] = {
            "available": env.get("available", False),
            "label": "Residuos solidos",
            "latest_year": env.get("latest_year"),
            "total_kg": env.get("total_kg"),
            "dataset_url": env.get("dataset_url"),
        }

    # Calidad de vida
    if isinstance(imcv_data, Exception):
        domains["calidad_vida"] = {"available": False, "reason": _safe_reason(imcv_data)}
    else:
        domains["calidad_vida"] = {
            "available": imcv_data.get("available", False),
            "label": "IMCV — Calidad de Vida",
            "latest_year": imcv_data.get("latest_year"),
            "total_comunas": len(imcv_data.get("by_comuna", [])),
            "dataset_url": imcv_data.get("dataset_url"),
        }

    # Siniestros viales
    if isinstance(sin, Exception):
        domains["siniestros_viales"] = {"available": False, "reason": _safe_reason(sin)}
    else:
        domains["siniestros_viales"] = {
            "available": sin.get("available", False),
            "label": "Victimas incidentes viales",
            "latest_year": sin.get("latest_year"),
            "total_victimas": sin.get("total_victimas"),
            "dataset_url": sin.get("dataset_url"),
        }

    # Violencia intrafamiliar
    if isinstance(vif, Exception):
        domains["violencia_intrafamiliar"] = {"available": False, "reason": _safe_reason(vif)}
    else:
        domains["violencia_intrafamiliar"] = {
            "available": vif.get("available", False),
            "label": "Violencia intrafamiliar",
            "latest_year": vif.get("latest_year"),
            "total": vif.get("total"),
            "dataset_url": vif.get("dataset_url"),
        }

    available_count = sum(1 for d in domains.values() if d.get("available"))
    return {
        "domains": domains,
        "available_domains": available_count,
        "total_domains": len(domains),
        "message": f"{available_count}/{len(domains)} dominios de datos disponibles en MEData.",
    }
