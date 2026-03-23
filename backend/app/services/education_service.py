"""
Servicio de Educacion.
Consume: directorio establecimientos educativos + indicadores ambiente escolar.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from .data_loader import load_education_establecimientos, load_education_ambiente_escolar
from ..utils.normalize import norm_key, normalize_code, resolve_optional_column

logger = logging.getLogger(__name__)


def get_establecimientos(comuna_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Directorio de establecimientos educativos por comuna.

    Columnas esperadas: NOMBRE, CODIGO_DANE, CODIGO_MUNICIPIO, NOMBRE_MUNICIPIO,
    CODIGO_COMUNA, NOMBRE_BARRIO, MODALIDAD, NUMERO_SEDES, NIVEL
    """
    df = load_education_establecimientos()
    if df is None:
        return {"available": False, "reason": "Dataset no disponible.", "establecimientos": [], "by_comuna": []}

    cols = {norm_key(c): c for c in df.columns}

    name_col = cols.get("nombre") or cols.get("nombreestablecimiento") or cols.get("institucion")
    comuna_col = (
        cols.get("codigocomuna")
        or cols.get("codcomuna")
        or cols.get("comuna")
        or cols.get("nombrecomunabarrio")
    )
    barrio_col = cols.get("nombrebarrio") or cols.get("barrio") or cols.get("nombrebarriovereda")
    modalidad_col = cols.get("modalidad") or cols.get("sector") or cols.get("caracter")
    nivel_col = cols.get("nivel") or cols.get("niveleducativo") or cols.get("grados")
    sedes_col = cols.get("numerosedes") or cols.get("sedes") or cols.get("numerosedesprincipal")

    df = df.copy()

    if comuna_col:
        df["_code"] = df[comuna_col].apply(normalize_code)
        if comuna_code:
            df = df[df["_code"] == normalize_code(comuna_code)]

    # Por comuna
    by_comuna: List[Dict[str, Any]] = []
    if comuna_col:
        agg = (
            df.groupby("_code", as_index=False)
            .size()
            .rename(columns={"_code": "comuna_code", "size": "establecimientos"})
            .sort_values("establecimientos", ascending=False)
        )
        by_comuna = agg.to_dict(orient="records")

    # Por modalidad (oficial/privado)
    by_modalidad: List[Dict[str, Any]] = []
    if modalidad_col:
        mod_agg = (
            df.groupby(modalidad_col, as_index=False)
            .size()
            .rename(columns={"size": "total", modalidad_col: "modalidad"})
            .sort_values("total", ascending=False)
        )
        by_modalidad = mod_agg.head(10).to_dict(orient="records")

    # Lista de establecimientos (limitada)
    establecimientos: List[Dict[str, Any]] = []
    keep_cols = [c for c in [name_col, comuna_col, barrio_col, modalidad_col, nivel_col, sedes_col] if c]
    if keep_cols:
        sample = df[keep_cols].head(200)
        establecimientos = sample.where(pd.notna(sample), None).to_dict(orient="records")

    return {
        "available": True,
        "total": len(df),
        "by_comuna": by_comuna,
        "by_modalidad": by_modalidad,
        "establecimientos": establecimientos,
        "dataset_url": "http://medata.gov.co/sites/default/files/distribution/1-011-08-000122/directorio_establecimientos_educativos.csv",
    }


def get_ambiente_escolar(year: Optional[int] = None) -> Dict[str, Any]:
    """
    Indicadores historicos de ambiente escolar (relaciones, comunicacion, participacion).
    """
    df = load_education_ambiente_escolar()
    if df is None:
        return {"available": False, "reason": "Dataset no disponible.", "indicadores": [], "series": []}

    cols = {norm_key(c): c for c in df.columns}

    year_col = cols.get("ao") or cols.get("anio") or cols.get("ano") or cols.get("year") or cols.get("vigencia")
    indicator_col = cols.get("indicador") or cols.get("nombreaspectocomponente") or cols.get("componente")
    value_col = cols.get("valor") or cols.get("resultado") or cols.get("puntaje") or cols.get("indice")
    institution_col = cols.get("nombreinstitucion") or cols.get("institucion") or cols.get("establecimiento")

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

    # Por indicador
    indicadores: List[Dict[str, Any]] = []
    if indicator_col and value_col:
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        agg = (
            df.groupby(indicator_col, as_index=False)[value_col]
            .mean()
            .rename(columns={indicator_col: "indicador", value_col: "promedio"})
            .sort_values("promedio", ascending=False)
        )
        indicadores = agg.head(15).to_dict(orient="records")

    # Serie temporal
    series: List[Dict[str, Any]] = []
    if year_col and value_col:
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        ts = df.groupby("_year", as_index=False)[value_col].mean().rename(columns={value_col: "promedio"})
        series = [{"year": int(r["_year"]), "promedio": float(r["promedio"]) if pd.notna(r["promedio"]) else None} for _, r in ts.iterrows()]

    return {
        "available": True,
        "latest_year": latest_year,
        "available_years": available_years,
        "total_registros": len(df),
        "indicadores": indicadores,
        "series": series,
        "dataset_url": "http://medata.gov.co/sites/default/files/distribution/1-011-08-000068/historico_indicadores_ambiente_escolar.csv",
    }
