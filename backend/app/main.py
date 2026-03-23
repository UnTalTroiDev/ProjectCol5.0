from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .schemas.dashboard import (
    ComunasResponse,
    CrimeStatsResponse,
    OverviewResponse,
    TrendsResponse,
)
from .services.dashboard_service import (
    get_crime_stats,
    get_dashboard_overview,
    get_dashboard_trends,
    get_territory_comunas,
)
from .utils.normalize import normalize_code

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MedCity Dashboard API",
    description="API para un dashboard de Medellín usando datos abiertos (MEData).",
    version="0.2.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["system"])
def health() -> dict:
    logger.info("Health check OK")
    return {"status": "ok"}


@app.get("/api/territory/comunas", response_model=ComunasResponse, tags=["territory"])
def comunas() -> ComunasResponse:
    result = get_territory_comunas()
    logger.info("GET /api/territory/comunas -> %d comunas", len(result))
    return ComunasResponse(comunas=result)


@app.get("/api/dashboard/overview", response_model=OverviewResponse, tags=["dashboard"])
def overview(
    comuna_code: str = Query(
        "ALL",
        description="Codigo normalizado de la comuna (ej: '04') o 'ALL'.",
        min_length=1,
        max_length=10,
    ),
    year: Optional[int] = Query(
        None,
        description="Año a consultar. Si se omite, se usa el ultimo disponible en cada dataset.",
        ge=2000,
        le=2100,
    ),
) -> OverviewResponse:
    comuna_code = comuna_code.strip()
    logger.info("GET /api/dashboard/overview?comuna_code=%s&year=%s", comuna_code, year)

    if comuna_code != "ALL":
        known_codes = {c["code"] for c in get_territory_comunas()}
        normalized = normalize_code(comuna_code)
        if normalized not in known_codes:
            logger.warning("comuna_code no encontrado: %r (normalizado: %r)", comuna_code, normalized)
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "NOT_FOUND",
                    "message": (
                        f"No existe la comuna con codigo '{comuna_code}'. "
                        "Use GET /api/territory/comunas para ver los codigos validos."
                    ),
                },
            )

    return get_dashboard_overview(comuna_code=comuna_code, year=year)


@app.get("/api/dashboard/trends", response_model=TrendsResponse, tags=["dashboard"])
def trends(
    metric: str = Query(
        ...,
        description="Metrica a consultar: 'mobility', 'safety' o 'investment'.",
    ),
    comuna_code: Optional[str] = Query(
        None,
        description="Codigo de comuna (ej: '04') o None/'ALL' para toda la ciudad.",
        max_length=10,
    ),
) -> TrendsResponse:
    valid_metrics = {"mobility", "safety", "investment"}
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_METRIC",
                "message": f"Metrica '{metric}' no valida. Valores aceptados: {sorted(valid_metrics)}.",
            },
        )

    logger.info("GET /api/dashboard/trends?metric=%s&comuna_code=%s", metric, comuna_code)
    result = get_dashboard_trends(metric=metric, comuna_code=comuna_code)
    return TrendsResponse(**result)


@app.get("/api/dashboard/crime-stats", response_model=CrimeStatsResponse, tags=["dashboard"])
def crime_stats(
    comuna_code: Optional[str] = Query(
        None,
        description="Codigo de comuna (ej: '04') o None/'ALL' para toda la ciudad.",
        max_length=10,
    ),
    year: Optional[int] = Query(
        None,
        description="Año a consultar. Si se omite, se usa el ultimo disponible.",
        ge=2000,
        le=2100,
    ),
) -> CrimeStatsResponse:
    logger.info("GET /api/dashboard/crime-stats?comuna_code=%s&year=%s", comuna_code, year)
    result = get_crime_stats(comuna_code=comuna_code, year=year)
    return CrimeStatsResponse(**result)
