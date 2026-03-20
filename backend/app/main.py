from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .schemas.dashboard import ComunasResponse, OverviewResponse
from .services.dashboard_service import get_dashboard_overview, get_territory_comunas


app = FastAPI(
    title="MedCity Dashboard API",
    description="API para un dashboard de Medellín usando datos abiertos (MEData).",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/territory/comunas", response_model=ComunasResponse)
def comunas() -> ComunasResponse:
    return ComunasResponse(comunas=get_territory_comunas())


@app.get("/api/dashboard/overview", response_model=OverviewResponse)
def overview(comuna_code: str = Query("ALL", description="Codigo normalizado de la comuna (ej: '04') o 'ALL'.")):
    comuna_code = comuna_code.strip()
    return get_dashboard_overview(comuna_code=comuna_code)

