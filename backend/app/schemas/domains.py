"""Pydantic response models for domain-specific endpoints."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CriminalidadResponse(BaseModel):
    available: bool
    available_years: List[int] = []
    filtered_year: Optional[int] = None
    filtered_crime_type: Optional[str] = None
    by_type: List[Dict[str, Any]] = []
    series: List[Dict[str, Any]] = []
    dataset_url: Optional[str] = None
    reason: Optional[str] = None


class ViolenciaIntrafamiliarResponse(BaseModel):
    available: bool
    latest_year: Optional[int] = None
    available_years: List[int] = []
    total: Optional[float] = None
    by_comuna: List[Dict[str, Any]] = []
    series: List[Dict[str, Any]] = []
    dataset_url: Optional[str] = None
    reason: Optional[str] = None


class NatalidadResponse(BaseModel):
    available: bool
    latest_year: Optional[int] = None
    available_years: List[int] = []
    total_nacimientos: Optional[int] = None
    by_comuna: List[Dict[str, Any]] = []
    by_sex: List[Dict[str, Any]] = []
    series: List[Dict[str, Any]] = []
    dataset_url: Optional[str] = None
    reason: Optional[str] = None


class HospitalizacionResponse(BaseModel):
    available: bool
    latest_year: Optional[int] = None
    available_years: List[int] = []
    total_egresos: Optional[int] = None
    avg_dias_estancia: Optional[float] = None
    by_diagnostico: List[Dict[str, Any]] = []
    series: List[Dict[str, Any]] = []
    dataset_url: Optional[str] = None
    reason: Optional[str] = None


class EstablecimientosResponse(BaseModel):
    available: bool
    total: Optional[int] = None
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    by_comuna: List[Dict[str, Any]] = []
    by_modalidad: List[Dict[str, Any]] = []
    establecimientos: List[Dict[str, Any]] = []
    dataset_url: Optional[str] = None
    reason: Optional[str] = None


class AmbienteEscolarResponse(BaseModel):
    available: bool
    latest_year: Optional[int] = None
    available_years: List[int] = []
    total_registros: Optional[int] = None
    indicadores: List[Dict[str, Any]] = []
    series: List[Dict[str, Any]] = []
    dataset_url: Optional[str] = None
    reason: Optional[str] = None


class ResiduosResponse(BaseModel):
    available: bool
    latest_year: Optional[int] = None
    available_years: List[int] = []
    total_kg: Optional[float] = None
    unit: str = "kg"
    by_type: List[Dict[str, Any]] = []
    series: List[Dict[str, Any]] = []
    dataset_url: Optional[str] = None
    reason: Optional[str] = None


class ImcvResponse(BaseModel):
    available: bool
    latest_year: Optional[int] = None
    available_years: List[int] = []
    by_comuna: List[Dict[str, Any]] = []
    by_dimension: List[Dict[str, Any]] = []
    series: List[Dict[str, Any]] = []
    dataset_url: Optional[str] = None
    reason: Optional[str] = None


class SiniestrosResponse(BaseModel):
    available: bool
    latest_year: Optional[int] = None
    available_years: List[int] = []
    total_victimas: Optional[int] = None
    by_type: List[Dict[str, Any]] = []
    by_severity: List[Dict[str, Any]] = []
    by_comuna: List[Dict[str, Any]] = []
    series: List[Dict[str, Any]] = []
    dataset_url: Optional[str] = None
    reason: Optional[str] = None


class CompareResponse(BaseModel):
    year: Optional[int] = None
    comunas: List[Dict[str, Any]] = []
