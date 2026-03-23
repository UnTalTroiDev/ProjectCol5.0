from typing import Any, Dict, List, Optional

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


class TrendPoint(BaseModel):
    year: int
    value: Optional[float]


class TrendsResponse(BaseModel):
    metric: str
    comuna_code: str
    unit: str
    series: List[TrendPoint]
    available_years: List[int]


class CrimeMetric(BaseModel):
    value: Optional[float]
    unit: str
    year: Optional[int]


class LesionesCrimeMetric(CrimeMetric):
    available: bool = False


class CrimeStatsResponse(BaseModel):
    comuna_code: str
    year: Optional[int]
    homicidios: CrimeMetric
    lesiones_comunes: LesionesCrimeMetric
    top_homicidios_by_comuna: List[Dict[str, Any]]
    top_lesiones_by_comuna: List[Dict[str, Any]]
