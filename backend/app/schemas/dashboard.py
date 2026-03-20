from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ComunaOption(BaseModel):
    code: str = Field(..., description="Codigo normalizado de la comuna (ej: '01').")
    name: Optional[str] = Field(None, description="Nombre de la comuna.")


class TerritorySummary(BaseModel):
    comuna_code: str
    comuna_name: Optional[str] = None


class MetricBlock(BaseModel):
    value: Optional[float]
    unit: str = ""


class OverviewResponse(BaseModel):
    meta: Dict[str, Any]
    selected: TerritorySummary
    metrics: Dict[str, MetricBlock]
    city_averages: Dict[str, MetricBlock]
    recommendations: List[str]
    mobility_by_comuna: List[Dict[str, Any]]
    safety_by_comuna: List[Dict[str, Any]]


class ComunasResponse(BaseModel):
    comunas: List[ComunaOption]

