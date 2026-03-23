"""
Servicio de Salud.
Consume: natalidad + hospitalizacion (Secretaria de Salud de Medellin).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from .data_loader import load_health_natalidad, load_health_hospitalizacion
from ..utils.normalize import norm_key, normalize_code

logger = logging.getLogger(__name__)


def get_natalidad(year: Optional[int] = None) -> Dict[str, Any]:
    """
    Nacimientos en Medellin por año, sexo y comuna.

    Columnas esperadas en natalidad.csv:
    AÑO / FECHA_NACIMIENTO, CODIGO_COMUNA, SEXO, PESO, TALLA, TIPO_PARTO
    """
    df = load_health_natalidad()
    if df is None:
        return {"available": False, "reason": "Dataset no disponible.", "by_comuna": [], "series": []}

    cols = {norm_key(c): c for c in df.columns}

    # Columna de año
    year_col = cols.get("ao") or cols.get("anio") or cols.get("ano") or cols.get("year")
    date_col = None
    if not year_col:
        for c in df.columns:
            nk = norm_key(c)
            if "fech" in nk and "nac" in nk:
                date_col = c
                break

    comuna_col = (
        cols.get("codigocomuna")
        or cols.get("codcomuna")
        or cols.get("comuna")
        or cols.get("codigomunicipio")
    )
    sex_col = cols.get("sexo") or cols.get("genero")

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
    else:
        return {"available": False, "reason": "No se encontro columna de año.", "by_comuna": [], "series": []}

    available_years = sorted(df["_year"].unique().astype(int).tolist())
    latest_year = year if year else int(df["_year"].max())

    if year:
        df = df[df["_year"] == year]

    total = len(df)

    # Por año (tendencia)
    ts = df.groupby("_year", as_index=False).size().rename(columns={"size": "nacimientos"})
    series = [{"year": int(r["_year"]), "nacimientos": int(r["nacimientos"])} for _, r in ts.iterrows()]

    # Por comuna
    by_comuna: List[Dict[str, Any]] = []
    if comuna_col:
        df["_code"] = df[comuna_col].apply(normalize_code)
        agg = (
            df.groupby("_code", as_index=False)
            .size()
            .rename(columns={"_code": "comuna_code", "size": "nacimientos"})
            .sort_values("nacimientos", ascending=False)
        )
        by_comuna = agg.to_dict(orient="records")

    # Por sexo
    by_sex: List[Dict[str, Any]] = []
    if sex_col:
        sex_agg = df.groupby(sex_col, as_index=False).size().rename(columns={"size": "total"})
        by_sex = sex_agg.to_dict(orient="records")

    return {
        "available": True,
        "latest_year": latest_year,
        "available_years": available_years,
        "total_nacimientos": total,
        "by_comuna": by_comuna,
        "by_sex": by_sex,
        "series": series,
        "dataset_url": "http://medata.gov.co/sites/default/files/distribution/1-026-22-000029/natalidad.csv",
    }


def get_hospitalizacion(year: Optional[int] = None) -> Dict[str, Any]:
    """
    Registros de hospitalizacion en Medellin por año y diagnostico.
    """
    df = load_health_hospitalizacion()
    if df is None:
        return {"available": False, "reason": "Dataset no disponible.", "by_diagnostico": [], "series": []}

    cols = {norm_key(c): c for c in df.columns}

    year_col = cols.get("ao") or cols.get("anio") or cols.get("ano") or cols.get("year")
    date_col = None
    if not year_col:
        for c in df.columns:
            if "fech" in norm_key(c):
                date_col = c
                break

    diag_col = (
        cols.get("diagnostico")
        or cols.get("causaegreso")
        or cols.get("causa")
        or cols.get("descripciondiagnostico")
    )
    sex_col = cols.get("sexo") or cols.get("genero")
    days_col = cols.get("diasestancia") or cols.get("estancia") or cols.get("dias")

    df = df.copy()

    if year_col:
        df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
        df = df.dropna(subset=[year_col])
        df["_year"] = df[year_col].astype(int)
    elif date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
        df = df.dropna(subset=[date_col])
        df["_year"] = df[date_col].dt.year
    else:
        return {"available": False, "reason": "No se encontro columna de año.", "by_diagnostico": [], "series": []}

    available_years = sorted(df["_year"].unique().astype(int).tolist())
    if year:
        df = df[df["_year"] == year]

    latest_year = year or int(df["_year"].max())

    # Serie temporal
    ts = df.groupby("_year", as_index=False).size().rename(columns={"size": "egresos"})
    series = [{"year": int(r["_year"]), "egresos": int(r["egresos"])} for _, r in ts.iterrows()]

    # Por diagnostico (top 10)
    by_diagnostico: List[Dict[str, Any]] = []
    if diag_col:
        agg = (
            df.groupby(diag_col, as_index=False)
            .size()
            .rename(columns={"size": "total", diag_col: "diagnostico"})
            .sort_values("total", ascending=False)
        )
        by_diagnostico = agg.head(10).to_dict(orient="records")

    # Promedio dias estancia
    avg_days: Optional[float] = None
    if days_col:
        avg_days = float(pd.to_numeric(df[days_col], errors="coerce").mean())

    return {
        "available": True,
        "latest_year": latest_year,
        "available_years": available_years,
        "total_egresos": len(df),
        "avg_dias_estancia": avg_days,
        "by_diagnostico": by_diagnostico,
        "series": series,
        "dataset_url": "http://medata.gov.co/sites/default/files/distribution/1-026-22-000126/registro_hospitalizacion_prestacion_servicios_medicos.csv",
    }
