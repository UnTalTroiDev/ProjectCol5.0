from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .schemas.dashboard import ComunasResponse, OverviewResponse
from .services.dashboard_service import get_dashboard_overview, get_territory_comunas
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
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS
# Leer origenes desde variable de entorno ALLOWED_ORIGINS (separados por coma).
# Ejemplo en .env: ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
# Default a los puertos tipicos de React/Vite para desarrollo local.
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


@app.get("/api/health")
def health() -> dict:
    logger.info("Health check OK")
    return {"status": "ok"}


@app.get("/api/territory/comunas", response_model=ComunasResponse)
def comunas() -> ComunasResponse:
    result = get_territory_comunas()
    logger.info("GET /api/territory/comunas -> %d comunas", len(result))
    return ComunasResponse(comunas=result)


@app.get("/api/dashboard/overview", response_model=OverviewResponse)
def overview(
    comuna_code: str = Query(
        "ALL",
        description="Codigo normalizado de la comuna (ej: '04') o 'ALL'.",
        min_length=1,
        max_length=10,
    ),
) -> OverviewResponse:
    comuna_code = comuna_code.strip()
    logger.info("GET /api/dashboard/overview?comuna_code=%s", comuna_code)

    # Validar que el codigo existe cuando no es ALL.
    if comuna_code != "ALL":
        known_codes = {c["code"] for c in get_territory_comunas()}
        normalized = normalize_code(comuna_code)
        if normalized not in known_codes:
            logger.warning("comuna_code no encontrado: %r (normalizado: %r)", comuna_code, normalized)
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "NOT_FOUND",
                    "message": f"No existe la comuna con codigo '{comuna_code}'. "
                               f"Use GET /api/territory/comunas para ver los codigos validos.",
                },
            )

    return get_dashboard_overview(comuna_code=comuna_code)

