"""
Servicio de Seguridad ampliado.
Consume: criminalidad consolidada (10 tipos de delito) + violencia intrafamiliar.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from .data_loader import load_security_criminalidad, load_social_violencia_intrafamiliar
from ..utils.normalize import norm_key, normalize_code, resolve_column, resolve_optional_column

logger = logging.getLogger(__name__)

# Tipos de delito esperados en el consolidado MEData.
CRIME_TYPES_ES = [
    "HOMICIDIO",
    "HURTO A PERSONAS",
    "HURTO A AUTOMOTORES",
    "HURTO A MOTOCICLETAS",
    "HURTO A RESIDENCIAS",
    "HURTO A COMERCIO",
    "LESIONES PERSONALES",
    "EXTORSION",
    "VIOLENCIA INTRAFAMILIAR",
    "DELITOS SEXUALES",
]


def get_criminalidad_consolidada(
    year: Optional[int] = None,
    crime_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Devuelve criminalidad consolidada por tipo de delito y año/mes.

    Args:
        year: Filtrar por año. None = todos los años disponibles.
        crime_type: Filtrar por tipo de delito (ej: 'HOMICIDIO'). None = todos.
    """
    df = load_security_criminalidad()
    if df is None:
        return {"available": False, "reason": "Dataset no disponible en MEData.", "series": [], "by_type": []}

    cols = {norm_key(c): c for c in df.columns}

    year_col = cols.get("ao") or cols.get("anio") or cols.get("ano") or cols.get("year") or cols.get("vigencia")
    month_col = cols.get("mes") or cols.get("month")
    type_col = (
        cols.get("conducta")
        or cols.get("tipohecho")
        or cols.get("tipo")
        or cols.get("delito")
        or cols.get("descripcion")
    )
    qty_col = cols.get("cantidad") or cols.get("casos") or cols.get("total")

    if not year_col:
        return {"available": False, "reason": "No se encontro columna de año.", "series": [], "by_type": []}

    df = df.copy()
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df = df.dropna(subset=[year_col])
    df[year_col] = df[year_col].astype(int)

    if year:
        df = df[df[year_col] == year]

    available_years = sorted(df[year_col].unique().tolist())

    # Agregacion por tipo de delito
    by_type: List[Dict[str, Any]] = []
    if type_col:
        qty_series = (
            pd.to_numeric(df[qty_col], errors="coerce").fillna(1)
            if qty_col
            else pd.Series([1] * len(df))
        )
        df["_qty"] = qty_series
        if crime_type:
            df = df[df[type_col].astype(str).str.upper().str.contains(crime_type.upper(), na=False)]
        agg = (
            df.groupby(type_col, as_index=False)["_qty"]
            .sum()
            .rename(columns={type_col: "crime_type", "_qty": "total"})
            .sort_values("total", ascending=False)
        )
        by_type = agg.head(15).to_dict(orient="records")

    # Serie temporal por año
    series: List[Dict[str, Any]] = []
    if qty_col:
        df["_qty"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(1)
    else:
        df["_qty"] = 1

    if month_col and not year:
        # Agrupar por año para tendencia
        ts = df.groupby(year_col, as_index=False)["_qty"].sum()
        series = [{"year": int(r[year_col]), "total": float(r["_qty"])} for _, r in ts.iterrows()]
    elif month_col and year:
        df[month_col] = pd.to_numeric(df[month_col], errors="coerce")
        ts = df.groupby(month_col, as_index=False)["_qty"].sum().dropna(subset=[month_col])
        series = [{"month": int(r[month_col]), "total": float(r["_qty"])} for _, r in ts.iterrows()]
    else:
        ts = df.groupby(year_col, as_index=False)["_qty"].sum()
        series = [{"year": int(r[year_col]), "total": float(r["_qty"])} for _, r in ts.iterrows()]

    return {
        "available": True,
        "available_years": available_years,
        "filtered_year": year,
        "filtered_crime_type": crime_type,
        "by_type": by_type,
        "series": series,
        "dataset_url": "http://medata.gov.co/sites/default/files/distribution/1-027-23-000306/consolidado_cantidad_casos_criminalidad_por_anio_mes.csv",
    }


def get_violencia_intrafamiliar(year: Optional[int] = None) -> Dict[str, Any]:
    """Solicitudes de medidas de proteccion por violencia intrafamiliar por comuna y año."""
    df = load_social_violencia_intrafamiliar()
    if df is None:
        return {"available": False, "reason": "Dataset no disponible.", "by_comuna": [], "series": []}

    cols = {norm_key(c): c for c in df.columns}

    date_col = cols.get("fechahecho") or cols.get("fecha") or cols.get("fechasolicitud")
    if not date_col:
        for c in df.columns:
            if "fech" in norm_key(c):
                date_col = c
                break

    comuna_col = cols.get("codigocomuna") or cols.get("comuna") or cols.get("barrio")
    qty_col = cols.get("cantidad") or cols.get("casos")

    df = df.copy()

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
        df = df.dropna(subset=[date_col])
        df["_year"] = df[date_col].dt.year
        available_years = sorted(df["_year"].dropna().astype(int).unique().tolist())
        if year:
            df = df[df["_year"] == year]
        latest_year = year or (int(df["_year"].max()) if not df.empty else None)
    else:
        available_years = []
        latest_year = None

    if qty_col:
        df["_qty"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(1)
    else:
        df["_qty"] = 1

    by_comuna: List[Dict[str, Any]] = []
    if comuna_col:
        df["_code"] = df[comuna_col].apply(normalize_code)
        agg = df.groupby("_code", as_index=False)["_qty"].sum().rename(
            columns={"_code": "comuna_code", "_qty": "casos"}
        ).sort_values("casos", ascending=False)
        by_comuna = agg.head(16).to_dict(orient="records")

    series: List[Dict[str, Any]] = []
    if date_col:
        ts = df.groupby("_year", as_index=False)["_qty"].sum().dropna(subset=["_year"])
        series = [{"year": int(r["_year"]), "total": float(r["_qty"])} for _, r in ts.iterrows()]

    return {
        "available": True,
        "latest_year": latest_year,
        "available_years": available_years,
        "total": float(df["_qty"].sum()),
        "by_comuna": by_comuna,
        "series": series,
        "dataset_url": "http://medata.gov.co/sites/default/files/distribution/1-027-23-000028/solicitud_de_medidas_de_proteccion_por_violencia_intrafamiliar.csv",
    }
