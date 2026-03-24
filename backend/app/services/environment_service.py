"""
Servicio de Medio Ambiente.
Consume: residuos solidos Centro Administrativo Distrital (Secretaria de Suministros).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from .data_loader import load_environment_residuos
from ..utils.normalize import norm_key

logger = logging.getLogger(__name__)


async def get_residuos_solidos(year: Optional[int] = None) -> Dict[str, Any]:
    """
    Generacion de residuos solidos del Centro Administrativo Distrital
    (ordinarios y aprovechables) por mes y año.

    Columnas esperadas: FECHA, AÑO, MES, TIPO_RESIDUO, CANTIDAD_KG
    """
    df = await load_environment_residuos()
    if df is None:
        return {"available": False, "reason": "Dataset no disponible.", "by_type": [], "series": []}

    cols = {norm_key(c): c for c in df.columns}

    date_col = cols.get("fecha") or cols.get("fecharegistro") or cols.get("periodo")
    year_col = cols.get("ao") or cols.get("anio") or cols.get("ano") or cols.get("year")
    month_col = cols.get("mes") or cols.get("month")
    type_col = (
        cols.get("tiporesiduo")
        or cols.get("tipo")
        or cols.get("clasesresiduo")
        or cols.get("clasificacion")
    )
    qty_col = (
        cols.get("cantidadkg")
        or cols.get("cantidad")
        or cols.get("kg")
        or cols.get("peso")
        or cols.get("toneladas")
    )

    df = df.copy()

    # Extraer año
    if year_col:
        df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
        df = df.dropna(subset=[year_col])
        df["_year"] = df[year_col].astype(int)
    elif date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
        df = df.dropna(subset=[date_col])
        df["_year"] = df[date_col].dt.year
        if not month_col:
            df["_month"] = df[date_col].dt.month
            month_col = "_month"
    else:
        return {"available": False, "reason": "No se encontro columna de fecha/año.", "by_type": [], "series": []}

    available_years = sorted(df["_year"].unique().astype(int).tolist())
    if year:
        df = df[df["_year"] == year]

    latest_year = year or int(df["_year"].max())

    qty_series = (
        pd.to_numeric(df[qty_col], errors="coerce").fillna(0)
        if qty_col
        else pd.Series([1.0] * len(df))
    )
    df["_qty"] = qty_series

    total_kg = float(df["_qty"].sum())

    # Por tipo de residuo
    by_type: List[Dict[str, Any]] = []
    if type_col and type_col in df.columns:
        agg = (
            df.groupby(type_col, as_index=False)["_qty"]
            .sum()
            .rename(columns={type_col: "tipo_residuo", "_qty": "cantidad_kg"})
            .sort_values("cantidad_kg", ascending=False)
        )
        by_type = agg.to_dict(orient="records")

    # Serie mensual (año seleccionado) o anual
    series: List[Dict[str, Any]] = []
    if year and month_col:
        month_col_real = "_month" if month_col == "_month" else month_col
        if month_col_real in df.columns:
            df[month_col_real] = pd.to_numeric(df[month_col_real], errors="coerce")
            ts = df.groupby(month_col_real, as_index=False)["_qty"].sum().dropna(subset=[month_col_real])
            series = [{"month": int(r[month_col_real]), "cantidad_kg": float(r["_qty"])} for _, r in ts.iterrows()]
    else:
        ts = df.groupby("_year", as_index=False)["_qty"].sum()
        series = [{"year": int(r["_year"]), "cantidad_kg": float(r["_qty"])} for _, r in ts.iterrows()]

    return {
        "available": True,
        "latest_year": latest_year,
        "available_years": available_years,
        "total_kg": total_kg,
        "unit": "kg",
        "by_type": by_type,
        "series": series,
        "dataset_url": "https://medata.gov.co/sites/default/files/distribution/1-028-02-000599/generacion_residuos_solidos_centro_administrativo_distrital.csv",
    }
