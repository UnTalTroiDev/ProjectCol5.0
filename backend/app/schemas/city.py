"""Schemas Pydantic para los nuevos dominios de ciudad."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class DatasetStatus(BaseModel):
    available: bool
    reason: Optional[str] = None
    dataset_url: Optional[str] = None


class CitySummaryResponse(BaseModel):
    """KPIs de alto nivel para todos los dominios de la ciudad."""
    domains: Dict[str, Dict[str, Any]]
    message: str = "Resumen de indicadores urbanos de Medellin por dominio."
