"""
Servicio de Calidad de Vida.
Consume: Indice Multidimensional Calidad de Vida (IMCV) por comuna.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from .data_loader import load_quality_imcv, load_mobility_siniestros
from ..utils.normalize import norm_key, normalize_code

logger = logging.getLogger(__name__)


def get_imcv(year: Optional[int] = None, comuna_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Indice Multidimensional Calidad de Vida por comuna y dimension.

    Columnas esperadas: AÑO, CODIGO_COMUNA, NOMBRE_COMUNA, DIMENSION, INDICADOR, VALOR
    """
    df = load_quality_imcv()
    if df is None:
        return {"available": False, "reason": "Dataset no disponible.", "by_comuna": [], "by_dimension": [], "series": []}

    cols = {norm_key(c): c for c in df.columns}

    year_col = cols.get("ao") or cols.get("anio") or cols.get("ano") or cols.get("year") or cols.get("vigencia")
    comuna_col = cols.get("codigocomuna") or cols.get("codcomuna") or cols.get("comuna")
    name_col = cols.get("nombrecomuna") or cols.get("nombre")
    dim_col = cols.get("dimension") or cols.get("componente") or cols.get("aspecto")
    indicator_col = cols.get("indicador") or cols.get("nombreaspectocomponente")
    value_col = cols.get("valor") or cols.get("indice") or cols.get("resultado") or cols.get("puntaje")

    df = df.copy()

    if year_col:
        df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
        df = df.dropna(subset=[year_col])
        df["_year"] = df[year_col].astype(int)
        available_years = sorted(df["_year"].unique().tolist())
        if year:
            df = df[df["_year"] == year]
        latest_year = year or int(df["_year"].max())
    else:
        available_years = []
        latest_year = None

    if value_col:
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

    if comuna_code and comuna_col:
        norm = normalize_code(comuna_code)
        df["_code"] = df[comuna_col].apply(normalize_code)
        df = df[df["_code"] == norm]

    # Por comuna (IMCV promedio)
    by_comuna: List[Dict[str, Any]] = []
    if comuna_col and value_col:
        df["_code"] = df[comuna_col].apply(normalize_code)
        grp_cols = ["_code"]
        if name_col and name_col in df.columns:
            grp_cols.append(name_col)
        agg = (
            df.groupby(grp_cols, as_index=False)[value_col]
            .mean()
            .rename(columns={"_code": "comuna_code", value_col: "imcv_promedio"})
            .sort_values("imcv_promedio", ascending=False)
        )
        by_comuna = agg.to_dict(orient="records")

    # Por dimension
    by_dimension: List[Dict[str, Any]] = []
    if dim_col and value_col and dim_col in df.columns:
        agg_dim = (
            df.groupby(dim_col, as_index=False)[value_col]
            .mean()
            .rename(columns={dim_col: "dimension", value_col: "promedio"})
            .sort_values("promedio", ascending=False)
        )
        by_dimension = agg_dim.to_dict(orient="records")

    # Serie temporal
    series: List[Dict[str, Any]] = []
    if year_col and value_col:
        ts = df.groupby("_year", as_index=False)[value_col].mean().rename(columns={value_col: "imcv_promedio"})
        series = [
            {"year": int(r["_year"]), "imcv_promedio": float(r["imcv_promedio"]) if pd.notna(r["imcv_promedio"]) else None}
            for _, r in ts.iterrows()
        ]

    return {
        "available": True,
        "latest_year": latest_year,
        "available_years": available_years,
        "by_comuna": by_comuna,
        "by_dimension": by_dimension,
        "series": series,
        "dataset_url": "http://medata.gov.co/sites/default/files/distribution/1-002-09-000041/indice_multidimensional_encuesta_calidad_de_vida.csv",
    }


def get_siniestros_viales(year: Optional[int] = None, comuna_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Victimas en incidentes viales por año, tipo de victima y comuna.
    """
    df = load_mobility_siniestros()
    if df is None:
        return {"available": False, "reason": "Dataset no disponible.", "by_type": [], "by_comuna": [], "series": []}

    cols = {norm_key(c): c for c in df.columns}

    date_col = cols.get("fechahecho") or cols.get("fecha") or cols.get("fechaincidente")
    if not date_col:
        for c in df.columns:
            if "fech" in norm_key(c):
                date_col = c
                break

    type_col = cols.get("tipovictima") or cols.get("tipo") or cols.get("clasevictima") or cols.get("condicionvictima")
    severity_col = cols.get("gravedadlesion") or cols.get("gravedad") or cols.get("condicion")
    comuna_col = cols.get("codigocomuna") or cols.get("comuna") or cols.get("barrio")

    df = df.copy()

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
        df = df.dropna(subset=[date_col])
        df["_year"] = df[date_col].dt.year
        available_years = sorted(df["_year"].dropna().astype(int).unique().tolist())
        if year:
            df = df[df["_year"] == year]
        latest_year = year or int(df["_year"].max())
    else:
        available_years = []
        latest_year = None

    if comuna_code and comuna_col:
        norm = normalize_code(comuna_code)
        df["_code"] = df[comuna_col].apply(normalize_code)
        df = df[df["_code"] == norm]

    # Por tipo de victima
    by_type: List[Dict[str, Any]] = []
    if type_col and type_col in df.columns:
        agg = (
            df.groupby(type_col, as_index=False)
            .size()
            .rename(columns={type_col: "tipo_victima", "size": "total"})
            .sort_values("total", ascending=False)
        )
        by_type = agg.head(10).to_dict(orient="records")

    # Por gravedad
    by_severity: List[Dict[str, Any]] = []
    if severity_col and severity_col in df.columns:
        agg_sev = (
            df.groupby(severity_col, as_index=False)
            .size()
            .rename(columns={severity_col: "gravedad", "size": "total"})
            .sort_values("total", ascending=False)
        )
        by_severity = agg_sev.to_dict(orient="records")

    # Por comuna
    by_comuna: List[Dict[str, Any]] = []
    if comuna_col and comuna_col in df.columns:
        df["_code"] = df[comuna_col].apply(normalize_code)
        agg_com = (
            df.groupby("_code", as_index=False)
            .size()
            .rename(columns={"_code": "comuna_code", "size": "victimas"})
            .sort_values("victimas", ascending=False)
        )
        by_comuna = agg_com.head(16).to_dict(orient="records")

    # Serie temporal
    series: List[Dict[str, Any]] = []
    if date_col:
        ts = df.groupby("_year", as_index=False).size().rename(columns={"size": "victimas"}).dropna(subset=["_year"])
        series = [{"year": int(r["_year"]), "victimas": int(r["victimas"])} for _, r in ts.iterrows()]

    return {
        "available": True,
        "latest_year": latest_year,
        "available_years": available_years,
        "total_victimas": len(df),
        "by_type": by_type,
        "by_severity": by_severity,
        "by_comuna": by_comuna,
        "series": series,
        "dataset_url": "http://medata.gov.co/sites/default/files/distribution/1-023-25-000360/Mede_Victimas_inci.csv",
    }
